"""In-memory job store with thread-safe operations."""

import threading
from collections import OrderedDict, defaultdict
from datetime import datetime

from yubal import AudioCodec

from yubal_api.core.enums import JobStatus
from yubal_api.core.models import AlbumInfo, Job, LogEntry
from yubal_api.core.types import Clock, IdGenerator, LogStatus


class JobStore:
    """In-memory job store with capacity limit.

    Thread-safe using threading.Lock. All operations are synchronous since
    they only involve in-memory data structures with no I/O.

    This is a dumb persistence layer. State transitions are managed by JobExecutor.
    Cancellation signaling uses CancelToken; this store only persists the final status.
    """

    MAX_JOBS = 20
    MAX_LOGS_PER_JOB = 50
    MAX_TOTAL_LOGS = 200
    TIMEOUT_SECONDS = 30 * 60  # 30 minutes

    def __init__(
        self,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        self._clock = clock
        self._id_generator = id_generator
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._logs: defaultdict[str, list[LogEntry]] = defaultdict(list)
        self._lock = threading.Lock()
        self._active_job_id: str | None = None

    def _remove_job_internal(self, job_id: str) -> None:
        """Remove a job and its associated data. Must be called with lock held."""
        del self._jobs[job_id]
        self._logs.pop(job_id, None)

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

    def update_job(
        self,
        job_id: str,
        status: JobStatus | None = None,
        progress: float | None = None,
        album_info: AlbumInfo | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> Job | None:
        """Update job fields. Caller is responsible for checking job state first."""
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

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

    def add_log(
        self,
        job_id: str,
        status: LogStatus,
        message: str,
    ) -> None:
        """Add a log entry for a job. Caller is responsible for checking job state."""
        with self._lock:
            if job_id not in self._jobs:
                return

            entry = LogEntry(
                timestamp=self._clock(),
                status=status,
                message=message,
            )
            self._logs[job_id].append(entry)

            # Trim logs per job if exceeded
            if len(self._logs[job_id]) > self.MAX_LOGS_PER_JOB:
                self._logs[job_id] = self._logs[job_id][-self.MAX_LOGS_PER_JOB :]

    def transition_job(
        self,
        job_id: str,
        status: JobStatus,
        message: str,
        progress: float | None = None,
        album_info: AlbumInfo | None = None,
        started_at: datetime | None = None,
    ) -> Job | None:
        """Atomically update job status and add log entry.

        This is the preferred method for job state transitions as it combines
        update_job() and add_log() into a single atomic operation.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            # Update job fields
            job.status = status
            if progress is not None:
                job.progress = progress
            if album_info is not None:
                job.album_info = album_info
            if started_at is not None:
                job.started_at = started_at

            # Clear active job if finished
            if job.status.is_finished:
                job.completed_at = self._clock()
                if self._active_job_id == job_id:
                    self._active_job_id = None

            # Add log entry
            entry = LogEntry(
                timestamp=self._clock(),
                status=status.value,
                message=message,
            )
            self._logs[job_id].append(entry)

            if len(self._logs[job_id]) > self.MAX_LOGS_PER_JOB:
                self._logs[job_id] = self._logs[job_id][-self.MAX_LOGS_PER_JOB :]

            return job

    def get_all_logs(self) -> list[LogEntry]:
        """Get all logs from all jobs, sorted chronologically."""
        with self._lock:
            all_logs: list[LogEntry] = []
            for job_id in self._jobs:
                if job_id in self._logs:
                    all_logs.extend(self._logs[job_id])
            # Sort by timestamp and limit
            all_logs.sort(key=lambda x: x.timestamp)
            return all_logs[-self.MAX_TOTAL_LOGS :]

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
