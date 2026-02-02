"""Job execution orchestration service."""

import asyncio
import logging
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any

from yubal import AudioCodec, CancelToken, cleanup_part_files

from yubal_api.db.repository import SubscriptionRepository
from yubal_api.domain.enums import JobSource, JobStatus, ProgressStep
from yubal_api.domain.job import ContentInfo, Job
from yubal_api.services.protocols import JobExecutionStore
from yubal_api.services.sync import SyncService

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
        audio_format: AudioCodec = AudioCodec.OPUS,
        cookies_path: Path | None = None,
        fetch_lyrics: bool = True,
        subscription_repository: SubscriptionRepository | None = None,
    ) -> None:
        """Initialize the job executor.

        Args:
            job_store: Store for job persistence (protocol-based for testability).
            base_path: Base directory for downloaded files.
            audio_format: Target audio format (opus, mp3, m4a).
            cookies_path: Optional path to cookies.txt for authenticated requests.
            fetch_lyrics: Whether to fetch lyrics from lrclib.net.
            subscription_repository: Optional repository to update subscription names.
        """
        self._job_store = job_store
        self._base_path = base_path
        self._audio_format = audio_format
        self._cookies_path = cookies_path
        self._fetch_lyrics = fetch_lyrics
        self._subscription_repository = subscription_repository

        # Track background tasks to prevent GC during execution
        self._background_tasks: set[asyncio.Task[Any]] = set()
        # Map job_id -> CancelToken for cancellation support
        self._cancel_tokens: dict[str, CancelToken] = {}

    def create_and_start_job(
        self,
        url: str,
        max_items: int | None = None,
        source: JobSource = JobSource.MANUAL,
    ) -> Job | None:
        """Create a new job and start it if ready.

        This is the primary entry point for job creation. It handles:
        - Creating the job with proper audio format from settings
        - Starting the job if a slot is available

        Args:
            url: The URL to download content from.
            max_items: Maximum number of items to download (None for all).
            source: Source of the job (manual API call or scheduler).

        Returns:
            The created Job, or None if queue is full.
        """
        result = self._job_store.create(url, self._audio_format, max_items, source)
        if result is None:
            return None

        job, should_start = result
        if should_start:
            self.start_job(job)

        return job

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

            self._job_store.transition(
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
                    partial(
                        self._job_store.transition,
                        job_id,
                        status,
                        progress=progress,
                        content_info=content_info,
                    )
                )

            # Run sync in thread pool
            sync_service = SyncService(
                self._base_path,
                self._audio_format,
                self._cookies_path,
                self._fetch_lyrics,
            )
            result = await asyncio.to_thread(
                sync_service.run,
                url,
                on_progress,
                cancel_token,
                max_items,
            )

            # Handle result (cancelled status already set by cancel_job API)
            if cancel_token.is_cancelled:
                pass  # Status already set, cleanup happens in finally block
            elif result.success:
                self._job_store.transition(
                    job_id,
                    JobStatus.COMPLETED,
                    progress=PROGRESS_COMPLETE,
                    content_info=result.content_info,
                    download_stats=result.download_stats,
                )
                # Update subscription metadata with latest info from YouTube Music
                if (
                    self._subscription_repository
                    and result.content_info
                    and result.content_info.title
                ):
                    self._subscription_repository.update_metadata_by_url(
                        url,
                        result.content_info.title,
                        result.content_info.thumbnail_url,
                    )
            else:
                error_msg = result.error or "Unknown error"
                logger.error("Job %s failed: %s", job_id[:8], error_msg)
                self._job_store.transition(job_id, JobStatus.FAILED)

        except Exception as e:
            logger.exception("Job %s failed with error: %s", job_id[:8], e)
            self._job_store.transition(job_id, JobStatus.FAILED)

        finally:
            # Clean up .part files if job was cancelled
            if cancel_token.is_cancelled:
                cleaned = cleanup_part_files(self._base_path)
                if cleaned:
                    logger.info("Cleaned up %d partial download(s)", cleaned)

            self._cancel_tokens.pop(job_id, None)

            # Release active job slot AFTER cleanup, then start next
            # This ensures no concurrent downloads
            self._job_store.release_active(job_id)
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
