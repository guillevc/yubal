import asyncio
from collections import OrderedDict
from collections.abc import Callable
from datetime import datetime

from yubal.core.enums import JobStatus
from yubal.core.models import AlbumInfo, Job, LogEntry


class JobStore:
    """Thread-safe in-memory job store with capacity limit."""

    MAX_JOBS = 50
    MAX_LOGS_PER_JOB = 100
    MAX_TOTAL_LOGS = 500
    TIMEOUT_SECONDS = 30 * 60  # 30 minutes

    def __init__(
        self,
        clock: Callable[[], datetime],
        id_generator: Callable[[], str],
    ) -> None:
        self._clock = clock
        self._id_generator = id_generator
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._logs: dict[str, list[LogEntry]] = {}  # job_id -> logs
        self._lock = asyncio.Lock()
        self._active_job_id: str | None = None
        self._cancellation_requested: set[str] = set()

    async def create_job(
        self, url: str, audio_format: str = "mp3"
    ) -> tuple[Job, bool] | None:
        """
        Create a new job.

        Returns (job, should_start_immediately) or None if queue is full.
        """
        async with self._lock:
            # Prune completed/failed jobs if at capacity
            while len(self._jobs) >= self.MAX_JOBS:
                pruneable = [j for j in self._jobs.values() if j.status.is_finished]
                if not pruneable:
                    return None  # Queue full, all jobs active/queued
                oldest = min(pruneable, key=lambda j: j.created_at)
                del self._jobs[oldest.id]
                self._logs.pop(oldest.id, None)
                self._cancellation_requested.discard(oldest.id)

            # Check if we should start immediately
            should_start = self._active_job_id is None

            # Create new job
            job = Job(
                id=self._id_generator(),
                url=url,
                audio_format=audio_format,
            )
            self._jobs[job.id] = job

            if should_start:
                self._active_job_id = job.id

            return job, should_start

    async def get_job(self, job_id: str) -> Job | None:
        """Get a job by ID. Also checks for timeout."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                self._check_timeout(job)
            return job

    async def get_all_jobs(self) -> list[Job]:
        """Get all jobs, oldest first (FIFO order)."""
        async with self._lock:
            # Check timeouts on all active jobs
            for job in self._jobs.values():
                self._check_timeout(job)
            return list(self._jobs.values())

    async def pop_next_pending(self) -> Job | None:
        """Get and activate the next pending job (FIFO). Returns None if none."""
        async with self._lock:
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

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Returns False if job doesn't exist or is already finished.
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            # Cannot cancel already finished jobs
            if job.status.is_finished:
                return False

            # Mark as cancelled
            self._cancellation_requested.add(job_id)
            job.status = JobStatus.CANCELLED
            job.completed_at = self._clock()

            # Clear active job if it matches
            if self._active_job_id == job_id:
                self._active_job_id = None

            return True

    def is_cancelled(self, job_id: str) -> bool:
        """Check if cancellation was requested for a job."""
        return job_id in self._cancellation_requested

    async def update_job(
        self,
        job_id: str,
        status: JobStatus | None = None,
        progress: float | None = None,
        album_info: AlbumInfo | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> Job | None:
        """Update job fields. Cancelled jobs cannot be updated."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            # Don't update cancelled jobs (prevents race conditions)
            if job.status == JobStatus.CANCELLED:
                return job

            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = progress
            if album_info is not None:
                job.album_info = album_info
            if started_at is not None:
                job.started_at = started_at
            if completed_at is not None:
                job.completed_at = completed_at

            # Clear active job if finished
            if job.status.is_finished:
                job.completed_at = job.completed_at or self._clock()
                if self._active_job_id == job_id:
                    self._active_job_id = None

            return job

    async def add_log(
        self,
        job_id: str,
        status: str,
        message: str,
    ) -> None:
        """Add a log entry for a job."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return

            # Don't add logs to cancelled jobs (prevents stale updates)
            if job.status == JobStatus.CANCELLED:
                return

            entry = LogEntry(
                timestamp=self._clock(),
                status=status,
                message=message,
            )

            if job_id not in self._logs:
                self._logs[job_id] = []
            self._logs[job_id].append(entry)

            # Trim logs per job if exceeded
            if len(self._logs[job_id]) > self.MAX_LOGS_PER_JOB:
                self._logs[job_id] = self._logs[job_id][-self.MAX_LOGS_PER_JOB :]

    async def get_all_logs(self) -> list[LogEntry]:
        """Get all logs from all jobs, sorted chronologically."""
        async with self._lock:
            all_logs: list[LogEntry] = []
            for job_id in self._jobs:
                if job_id in self._logs:
                    all_logs.extend(self._logs[job_id])
            # Sort by timestamp and limit
            all_logs.sort(key=lambda x: x.timestamp)
            return all_logs[-self.MAX_TOTAL_LOGS :]

    async def delete_job(self, job_id: str) -> bool:
        """
        Delete a job.

        Returns False if job doesn't exist or is still running.
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if not job.status.is_finished:
                return False  # Cannot delete running job

            del self._jobs[job_id]
            self._logs.pop(job_id, None)
            self._cancellation_requested.discard(job_id)
            return True

    async def clear_completed(self) -> int:
        """
        Clear all completed/failed/cancelled jobs.

        Returns the number of jobs removed.
        """
        async with self._lock:
            to_remove = [
                job_id for job_id, job in self._jobs.items() if job.status.is_finished
            ]
            for job_id in to_remove:
                del self._jobs[job_id]
                self._logs.pop(job_id, None)
                self._cancellation_requested.discard(job_id)
            return len(to_remove)

    def _check_timeout(self, job: Job) -> bool:
        """
        Check if job has timed out. Must be called with lock held.

        Returns True if job was timed out.
        """
        if job.started_at and not job.status.is_finished:
            elapsed = self._clock() - job.started_at
            if elapsed.total_seconds() > self.TIMEOUT_SECONDS:
                job.status = JobStatus.FAILED
                job.completed_at = self._clock()
                if self._active_job_id == job.id:
                    self._active_job_id = None
                return True
        return False
