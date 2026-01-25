"""Job execution orchestration service."""

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from yubal_api.core.enums import JobStatus, ProgressStep
from yubal_api.core.models import ContentInfo, Job
from yubal_api.services.protocols import JobExecutionStore
from yubal_api.services.sync.cancel import CancelToken
from yubal_api.services.sync_service import SyncService

logger = logging.getLogger(__name__)

PROGRESS_COMPLETE = 100.0


class JobExecutor:
    """Orchestrates job execution lifecycle.

    This executor manages background job execution with proper cleanup and
    cancellation support. Jobs run in a thread pool to avoid blocking the
    async event loop during I/O-heavy operations (yt-dlp downloads).

    Key Responsibilities:
        - Background task lifecycle (creation, tracking, cleanup)
        - Cancellation via CancelToken registry
        - Job queue continuation (starts next pending job when one completes)
        - Progress callback wiring to update job store

    Architecture Notes:
        - Uses JobExecutionStore protocol for persistence (ISP compliance)
        - CancelToken is the single source of truth for cancellation
        - Tasks are tracked in a set to prevent garbage collection
    """

    def __init__(
        self,
        job_store: JobExecutionStore,
        base_path: Path,
        audio_format: str = "opus",
        cookies_path: Path | None = None,
    ) -> None:
        """Initialize the job executor.

        Args:
            job_store: Store for job persistence (protocol-based for testability).
            base_path: Base directory for downloaded files.
            audio_format: Target audio format (opus, mp3, m4a).
            cookies_path: Optional path to cookies.txt for authenticated requests.
        """
        self._job_store = job_store
        self._base_path = base_path
        self._audio_format = audio_format
        self._cookies_path = cookies_path

        # Track background tasks to prevent GC during execution
        self._background_tasks: set[asyncio.Task[Any]] = set()
        # Map job_id -> CancelToken for cancellation support
        self._cancel_tokens: dict[str, CancelToken] = {}

    def start_job(self, job: Job) -> None:
        """Start a job as a background task.

        The task is tracked to prevent garbage collection and will
        automatically trigger the next pending job when complete.

        Args:
            job: The job to start executing.
        """
        task = asyncio.create_task(
            self._run_job(job.id, job.url, job.max_items),
            name=f"job-{job.id[:8]}",  # Helpful for debugging
        )
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def cancel_job(self, job_id: str) -> bool:
        """Signal cancellation for a running job.

        This sets the cancel token which will be checked during download.
        The actual job status update happens in _run_job when it detects
        the cancellation.

        Args:
            job_id: ID of the job to cancel.

        Returns:
            True if a cancel token existed (job was running), False otherwise.
        """
        token = self._cancel_tokens.get(job_id)
        if token is None:
            return False

        token.cancel()
        logger.info("Job cancellation requested: %s", job_id[:8])
        return True

    def cancel_all_jobs(self) -> int:
        """Cancel all running jobs. Used during shutdown.

        Returns:
            Number of jobs that were signalled for cancellation.
        """
        tokens = list(self._cancel_tokens.values())
        for token in tokens:
            token.cancel()
        return len(tokens)

    async def _run_job(
        self, job_id: str, url: str, max_items: int | None = None
    ) -> None:
        """Background task that runs the sync operation."""
        cancel_token = CancelToken()
        self._cancel_tokens[job_id] = cancel_token

        try:
            # Check cancellation before starting (CancelToken is single source of truth)
            if cancel_token.is_cancelled:
                return

            self._job_store.transition_job(
                job_id,
                JobStatus.FETCHING_INFO,
                started_at=datetime.now(UTC),
            )

            # Create progress callback that updates job store
            loop = asyncio.get_running_loop()

            def on_progress(
                step: ProgressStep,
                _message: str,
                progress: float | None,
                details: dict[str, Any] | None,
            ) -> None:
                if cancel_token.is_cancelled:
                    return

                status = self._step_to_status(step)
                content_info = self._parse_content_info(details) if details else None

                # Skip terminal states - handled by result
                if status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    return

                loop.call_soon_threadsafe(
                    self._job_store.transition_job,
                    job_id,
                    status,
                    progress,
                    content_info,
                )

            # Run sync in thread pool
            sync_service = SyncService(
                self._base_path, self._audio_format, self._cookies_path
            )
            result = await asyncio.to_thread(
                sync_service.execute,
                url,
                on_progress,
                cancel_token,
                max_items,
            )

            # Handle result
            if cancel_token.is_cancelled:
                self._job_store.transition_job(job_id, JobStatus.CANCELLED)
            elif result.success:
                self._job_store.transition_job(
                    job_id,
                    JobStatus.COMPLETED,
                    progress=PROGRESS_COMPLETE,
                    content_info=result.content_info,
                    download_stats=result.download_stats,
                )
            else:
                error_msg = result.error or "Unknown error"
                logger.error("Job %s failed: %s", job_id[:8], error_msg)
                self._job_store.transition_job(job_id, JobStatus.FAILED)

        except Exception as e:
            logger.exception("Job %s failed with error: %s", job_id[:8], e)
            self._job_store.transition_job(job_id, JobStatus.FAILED)

        finally:
            self._cancel_tokens.pop(job_id, None)
            self._start_next_pending()

    @staticmethod
    def _step_to_status(step: ProgressStep) -> JobStatus:
        """Map progress step to job status."""
        return {
            ProgressStep.FETCHING_INFO: JobStatus.FETCHING_INFO,
            ProgressStep.DOWNLOADING: JobStatus.DOWNLOADING,
            ProgressStep.IMPORTING: JobStatus.IMPORTING,
            ProgressStep.COMPLETED: JobStatus.COMPLETED,
            ProgressStep.FAILED: JobStatus.FAILED,
        }.get(step, JobStatus.DOWNLOADING)

    @staticmethod
    def _parse_content_info(details: dict[str, Any]) -> ContentInfo | None:
        """Extract content info from details dict."""
        if data := details.get("content_info"):
            try:
                return ContentInfo(**data)
            except (TypeError, ValueError) as e:
                logger.warning("Failed to parse content info: %s", e)
        return None

    def _start_next_pending(self) -> None:
        """Start the next pending job if any."""
        if next_job := self._job_store.pop_next_pending():
            self.start_job(next_job)
