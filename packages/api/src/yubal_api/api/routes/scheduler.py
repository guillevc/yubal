"""Scheduler status endpoint."""

from fastapi import APIRouter

from yubal_api.api.deps import RepositoryDep, SchedulerDep, SettingsDep
from yubal_api.schemas.scheduler import SchedulerStatus, SubscriptionCounts

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("", response_model=SchedulerStatus)
def get_scheduler_status(
    repository: RepositoryDep,
    scheduler: SchedulerDep,
    settings: SettingsDep,
) -> SchedulerStatus:
    """Get scheduler status (read-only)."""
    return SchedulerStatus(
        running=scheduler.is_running,
        enabled=scheduler.enabled,
        cron_expression=scheduler.cron_expression,
        timezone=settings.tz,
        next_run_at=scheduler.next_run_at,
        subscription_counts=SubscriptionCounts(
            total=repository.count(),
            enabled=repository.count(enabled=True),
        ),
    )
