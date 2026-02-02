"""Service protocols for dependency injection."""

from datetime import datetime
from typing import Protocol

from yubal import AudioCodec, PhaseStats

from yubal_api.domain.enums import JobSource, JobStatus
from yubal_api.domain.job import ContentInfo, Job


class JobExecutionStore(Protocol):
    """Narrow interface for job execution operations.

    This protocol defines the minimal interface that JobExecutor needs,
    following the Interface Segregation Principle.

    All methods are synchronous as they only operate on in-memory data.
    """

    def create(
        self,
        url: str,
        audio_format: AudioCodec,
        max_items: int | None = None,
        source: JobSource = JobSource.MANUAL,
    ) -> tuple[Job, bool] | None:
        """Create a new job.

        Returns:
            Tuple of (job, should_start) or None if queue is full.
        """
        ...

    def transition(
        self,
        job_id: str,
        status: JobStatus,
        *,
        progress: float | None = None,
        content_info: ContentInfo | None = None,
        download_stats: PhaseStats | None = None,
        started_at: datetime | None = None,
    ) -> Job | None:
        """Update job status atomically."""
        ...

    def pop_next_pending(self) -> Job | None:
        """Get and activate the next pending job."""
        ...

    def release_active(self, job_id: str) -> bool:
        """Release the active job slot after execution ends.

        Returns:
            True if released, False if job was not the active job.
        """
        ...
