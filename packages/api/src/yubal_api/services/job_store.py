"""In-memory job store with thread-safe operations."""

import logging
import threading
from collections import OrderedDict
from datetime import datetime

from yubal import AudioCodec, PhaseStats

from yubal_api.core.enums import JobStatus
from yubal_api.core.models import AlbumInfo, Job
from yubal_api.core.types import Clock, IdGenerator

logger = logging.getLogger(__name__)


class JobStore:
    """In-memory job store with capacity limit and FIFO queue semantics.

    Thread-Safety:
        All public methods are thread-safe using a single lock. Operations are
        synchronous since they only involve in-memory data structures.

    Responsibilities:
        - Job persistence (CRUD operations)
        - Queue management (FIFO ordering, capacity limits)
        - Timeout detection for stalled jobs

    Non-Responsibilities:
        - State machine validation (caller's responsibility)
        - Cancellation signaling (handled by CancelToken in JobExecutor)

    Capacity:
        When at MAX_JOBS, completed jobs are pruned to make room for new ones.
        If all jobs are active/queued, job creation returns None.
    """

    MAX_JOBS = 20
    TIMEOUT_SECONDS = 30 * 60  # 30 minutes

    def __init__(
        self,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        """Initialize job store with injectable dependencies.

        Args:
            clock: Function returning current datetime (enables testing).
            id_generator: Function generating unique job IDs.
        """
        self._clock = clock
        self._id_generator = id_generator
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._lock = threading.Lock()
        self._active_job_id: str | None = None

    def _remove_job_internal(self, job_id: str) -> None:
        """Remove a job. Must be called with lock held."""
        del self._jobs[job_id]

    def create_job(
        self,
        url: str,
        audio_format: AudioCodec = AudioCodec.OPUS,
        max_items: int | None = None,
    ) -> tuple[Job, bool] | None:
        """Create a new job.

        Returns (job, should_start_immediately) or None if queue is full.
        """
        with self._lock:
            # Prune completed/failed jobs if at capacity
            while len(self._jobs) >= self.MAX_JOBS:
                pruneable = [j for j in self._jobs.values() if j.status.is_finished]
                if not pruneable:
                    return None  # Queue full, all jobs active/queued
                oldest = min(pruneable, key=lambda j: j.created_at)
                self._remove_job_internal(oldest.id)

            # Check if we should start immediately
            should_start = self._active_job_id is None

            # Create new job
            job = Job(
                id=self._id_generator(),
                url=url,
                audio_format=audio_format,
                max_items=max_items,
            )
            self._jobs[job.id] = job

            if should_start:
                self._active_job_id = job.id

            return job, should_start

    def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID. Also checks for timeout."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                self._check_timeout(job)
            return job

    def get_all_jobs(self) -> list[Job]:
        """Get all jobs, oldest first (FIFO order)."""
        with self._lock:
            # Check timeouts on all active jobs
            for job in self._jobs.values():
                self._check_timeout(job)
            return list(self._jobs.values())

    def pop_next_pending(self) -> Job | None:
        """Get and activate the next pending job (FIFO). Returns None if none."""
        with self._lock:
            pending = [
                j
                for j in self._jobs.values()
                if j.status == JobStatus.PENDING and j.id != self._active_job_id
            ]
            if not pending:
                return None
            oldest = min(pending, key=lambda j: j.created_at)
            self._active_job_id = oldest.id
            return oldest

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job.

        Returns False if job doesn't exist or is already finished.
        Cancellation signaling is handled by CancelToken in JobExecutor.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.status.is_finished:
                return False

            job.status = JobStatus.CANCELLED
            job.completed_at = self._clock()

            if self._active_job_id == job_id:
                self._active_job_id = None

            return True

    def _apply_job_updates(
        self,
        job: Job,
        status: JobStatus | None = None,
        progress: float | None = None,
        album_info: AlbumInfo | None = None,
        download_stats: PhaseStats | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Apply updates to a job. Must be called with lock held."""
        if status is not None:
            job.status = status
        if progress is not None:
            job.progress = progress
        if album_info is not None:
            job.album_info = album_info
        if download_stats is not None:
            job.download_stats = download_stats
        if started_at is not None:
            job.started_at = started_at
        if completed_at is not None:
            job.completed_at = completed_at

        # Clear active job if finished
        if job.status.is_finished:
            job.completed_at = job.completed_at or self._clock()
            if self._active_job_id == job.id:
                self._active_job_id = None

    def transition_job(
        self,
        job_id: str,
        status: JobStatus,
        progress: float | None = None,
        album_info: AlbumInfo | None = None,
        download_stats: PhaseStats | None = None,
        started_at: datetime | None = None,
    ) -> Job | None:
        """Update job status atomically."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            self._apply_job_updates(
                job, status, progress, album_info, download_stats, started_at
            )
            return job

    def delete_job(self, job_id: str) -> bool:
        """Delete a job.

        Returns False if job doesn't exist or is still running.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if not job.status.is_finished:
                return False  # Cannot delete running job

            self._remove_job_internal(job_id)
            logger.debug("Job removed: %s", job_id[:8])
            return True

    def clear_completed(self) -> int:
        """Clear all completed/failed/cancelled jobs.

        Returns the number of jobs removed.
        """
        with self._lock:
            to_remove = [
                job_id for job_id, job in self._jobs.items() if job.status.is_finished
            ]
            for job_id in to_remove:
                self._remove_job_internal(job_id)
            return len(to_remove)

    def _check_timeout(self, job: Job) -> bool:
        """Check if job has timed out. Must be called with lock held.

        A job times out if it has been running for longer than TIMEOUT_SECONDS.
        Timed-out jobs are marked as FAILED.

        Returns:
            True if job was timed out and marked as failed.
        """
        if not job.started_at or job.status.is_finished:
            return False

        elapsed = self._clock() - job.started_at
        if elapsed.total_seconds() <= self.TIMEOUT_SECONDS:
            return False

        # Mark job as failed due to timeout
        job.status = JobStatus.FAILED
        job.completed_at = self._clock()
        if self._active_job_id == job.id:
            self._active_job_id = None

        logger.warning(
            "Job %s timed out after %d seconds",
            job.id[:8],
            int(elapsed.total_seconds()),
        )
        return True
