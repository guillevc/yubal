"""Scheduler status schemas."""

from pydantic import BaseModel

from yubal_api.schemas.types import UTCDateTime


class SubscriptionCounts(BaseModel):
    """Subscription count statistics."""

    total: int
    enabled: int


class SchedulerStatus(BaseModel):
    """Scheduler status response."""

    running: bool
    enabled: bool
    cron_expression: str
    timezone: str
    next_run_at: UTCDateTime | None
    subscription_counts: SubscriptionCounts
