"""Job execution orchestration service."""

import asyncio
from datetime import UTC, datetime
from typing import Any

from yubal.core.callbacks import ProgressCallback, ProgressEvent
from yubal.core.enums import ImportType, JobStatus
from yubal.core.models import AlbumInfo, Job, SyncResult
from yubal.core.utils import detect_import_type
from yubal.services.job_store import JobStore
from yubal.services.sync import (
    AlbumSyncService,
    CallbackProgressEmitter,
    CancelToken,
    PlaylistSyncService,
)

PROGRESS_COMPLETE = 100.0


class JobExecutor:
    """Orchestrates job execution lifecycle.

    Manages:
    - Background task tracking (prevents GC)
    - Cancel token registry
    - Job queue continuation
    - Progress callback wiring
    """

    def __init__(
        self,
        job_store: JobStore,
        album_sync_service: AlbumSyncService,
        playlist_sync_service: PlaylistSyncService,
    ) -> None:
        self._job_store = job_store
        self._album_sync_service = album_sync_service
        self._playlist_sync_service = playlist_sync_service

        # Internal state
        self._background_tasks: set[asyncio.Task[Any]] = set()
        self._cancel_tokens: dict[str, CancelToken] = {}

    def start_job(self, job: Job) -> None:
        """Start a job as a background task with proper cleanup."""
        task = asyncio.create_task(self._run_job(job.id, job.url))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)

    def cancel_job(self, job_id: str) -> bool:
        """Signal cancellation for a running job.

        Returns True if a cancel token existed (job was running).
        """
        if job_id in self._cancel_tokens:
            self._cancel_tokens[job_id].cancel()
            return True
        return False

    async def _run_job(self, job_id: str, url: str) -> None:
        """Background task that runs the sync operation."""
        cancel_token = CancelToken()
        self._cancel_tokens[job_id] = cancel_token

        try:
            if self._job_store.is_cancelled(job_id):
                cancel_token.cancel()
                return

            await self._job_store.update_job(
                job_id,
                status=JobStatus.FETCHING_INFO,
                started_at=datetime.now(UTC),
            )
            await self._job_store.add_log(
                job_id, "fetching_info", f"Starting sync from: {url}"
            )

            progress_callback = self._create_progress_callback(job_id, cancel_token)
            progress_emitter = CallbackProgressEmitter(progress_callback)

            import_type = detect_import_type(url)
            sync_service = (
                self._album_sync_service
                if import_type == ImportType.ALBUM
                else self._playlist_sync_service
            )

            result = await asyncio.to_thread(
                sync_service.execute,
                url,
                job_id,
                progress_emitter,
                cancel_token,
            )

            if self._job_store.is_cancelled(job_id) or cancel_token.is_cancelled():
                await self._job_store.add_log(
                    job_id, "cancelled", "Job cancelled by user"
                )
                return

            await self._finalize_job(job_id, result)

        except Exception as e:
            await self._job_store.update_job(job_id, status=JobStatus.FAILED)
            await self._job_store.add_log(job_id, "failed", str(e))

        finally:
            self._cancel_tokens.pop(job_id, None)
            await self._start_next_pending()

    def _create_progress_callback(
        self, job_id: str, cancel_token: CancelToken
    ) -> ProgressCallback:
        """Create thread-safe progress callback for a job."""
        loop = asyncio.get_running_loop()

        def callback(event: ProgressEvent) -> None:
            if self._job_store.is_cancelled(job_id) or cancel_token.is_cancelled():
                return

            new_status = self._map_event_to_status(event)
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(
                    self._update_job_from_event(job_id, new_status, event)
                )
            )

        return callback

    @staticmethod
    def _map_event_to_status(event: ProgressEvent) -> JobStatus:
        """Map progress event step to job status."""
        status_map = {
            "fetching_info": JobStatus.FETCHING_INFO,
            "downloading": JobStatus.DOWNLOADING,
            "importing": JobStatus.IMPORTING,
            "completed": JobStatus.COMPLETED,
            "failed": JobStatus.FAILED,
        }
        return status_map.get(event.step.value, JobStatus.DOWNLOADING)

    async def _update_job_from_event(
        self, job_id: str, new_status: JobStatus, event: ProgressEvent
    ) -> None:
        """Update job state from progress event."""
        if self._job_store.is_cancelled(job_id):
            return

        # Skip completed/failed from callback - final result handles those
        if event.step.value in ("completed", "failed"):
            return

        album_info = self._parse_album_info(event)

        await self._job_store.update_job(
            job_id,
            status=new_status,
            progress=event.progress if event.progress is not None else None,
            album_info=album_info,
        )
        await self._job_store.add_log(job_id, event.step.value, event.message)

    @staticmethod
    def _parse_album_info(event: ProgressEvent) -> AlbumInfo | None:
        """Extract album info from event details if present."""
        details = event.details or {}
        album_info_data = details.get("album_info")
        if album_info_data and isinstance(album_info_data, dict):
            try:
                return AlbumInfo(**album_info_data)
            except Exception:  # noqa: S110
                pass
        return None

    async def _finalize_job(self, job_id: str, result: SyncResult) -> None:
        """Update job with final sync result."""
        if result.success:
            if result.destination:
                complete_msg = f"Sync complete: {result.destination}"
            elif result.album_info:
                complete_msg = f"Sync complete: {result.album_info.title}"
            else:
                complete_msg = "Sync complete"

            await self._job_store.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=PROGRESS_COMPLETE,
                album_info=result.album_info,
            )
            await self._job_store.add_log(job_id, "completed", complete_msg)
        else:
            await self._job_store.update_job(job_id, status=JobStatus.FAILED)
            await self._job_store.add_log(
                job_id, "failed", result.error or "Sync failed"
            )

    async def _start_next_pending(self) -> None:
        """Start the next pending job if any."""
        if next_job := await self._job_store.pop_next_pending():
            self.start_job(next_job)
