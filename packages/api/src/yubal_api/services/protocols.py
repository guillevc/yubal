"""Service protocols for dependency injection."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from yubal import AudioCodec, PhaseStats

from yubal_api.db.subscription import Subscription, SubscriptionFields, SubscriptionType
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
        subscription_id: UUID | None = None,
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


class SubscriptionRepository(Protocol):
    """Narrow interface for subscription data access."""

    def list(
        self,
        *,
        enabled: bool | None = None,
        type: SubscriptionType | None = None,
    ) -> list[Subscription]: ...

    def get(self, id: UUID) -> Subscription | None: ...

    def get_by_url(self, url: str) -> Subscription | None: ...

    def create(self, subscription: Subscription) -> Subscription: ...

    def update(self, id: UUID, fields: SubscriptionFields) -> Subscription | None: ...

    def delete(self, id: UUID) -> bool: ...

    def count(
        self,
        *,
        enabled: bool | None = None,
        type: SubscriptionType | None = None,
    ) -> int: ...
