"""Background scheduler for periodic subscription syncing."""

import asyncio
import logging
from datetime import UTC, datetime

from croniter import croniter

from yubal_api.db.repository import SubscriptionRepository
from yubal_api.db.subscription import Subscription
from yubal_api.domain.enums import JobSource
from yubal_api.services.job_executor import JobExecutor
from yubal_api.settings import Settings

logger = logging.getLogger(__name__)


class Scheduler:
    """Background scheduler that syncs enabled subscriptions periodically."""

    def __init__(
        self,
        repository: SubscriptionRepository,
        job_executor: JobExecutor,
        settings: Settings,
    ) -> None:
        """Initialize scheduler."""
        self._repository = repository
        self._job_executor = job_executor
        self._settings = settings
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._next_run_at: datetime | None = None

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._task is not None and not self._task.done()

    @property
    def enabled(self) -> bool:
        """Check if scheduler is enabled (from settings)."""
        return self._settings.scheduler_enabled

    @property
    def cron_expression(self) -> str:
        """Get cron expression (from settings)."""
        return self._settings.scheduler_cron

    @property
    def next_run_at(self) -> datetime | None:
        """Get next scheduled run time."""
        return self._next_run_at

    def _get_next_run_time(self) -> datetime:
        """Calculate next run time using croniter in configured timezone."""
        tz = self._settings.timezone
        cron = croniter(self._settings.scheduler_cron, datetime.now(tz))
        next_time = cron.get_next(datetime)
        # Convert to UTC for storage/comparison
        if next_time.tzinfo is None:
            next_time = next_time.replace(tzinfo=tz)
        return next_time.astimezone(UTC)

    def start(self) -> None:
        """Start the scheduler background task."""
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler background task."""
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        self._next_run_at = None
        logger.info("Scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            next_run = self._get_next_run_time()
            self._next_run_at = next_run if self._settings.scheduler_enabled else None
            wait_seconds = (next_run - datetime.now(UTC)).total_seconds()

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=max(0, wait_seconds),
                )
                break  # Stop event was set
            except TimeoutError:
                pass  # Timeout expired, time to sync

            if self._settings.scheduler_enabled:
                await self._sync_all_enabled()

    def _create_jobs_for_subscriptions(
        self, subscriptions: list[Subscription]
    ) -> list[str]:
        """Create sync jobs for given subscriptions."""
        job_ids: list[str] = []
        for subscription in subscriptions:
            try:
                job = self._job_executor.create_and_start_job(
                    subscription.url, subscription.max_items, JobSource.SCHEDULER
                )
                if job is None:
                    logger.warning(
                        "Could not create job for %s (queue full)",
                        subscription.name,
                    )
                    continue

                job_ids.append(job.id)
                self._repository.update(
                    subscription.id,
                    last_synced_at=datetime.now(UTC),
                )
                logger.info(
                    "Created sync job %s for %s",
                    job.id[:8],
                    subscription.name,
                )
            except Exception:
                logger.exception(
                    "Failed to create job for %s",
                    subscription.name,
                )
        return job_ids

    async def _sync_all_enabled(self) -> list[str]:
        """Sync all enabled subscriptions (async wrapper)."""
        return self._create_jobs_for_subscriptions(self._repository.list(enabled=True))

    def sync_subscription(self, subscription_id: str) -> str | None:
        """Create sync job for a single subscription. Returns job_id or None."""
        from uuid import UUID

        subscription = self._repository.get(UUID(subscription_id))
        if subscription is None:
            return None

        job_ids = self._create_jobs_for_subscriptions([subscription])
        return job_ids[0] if job_ids else None

    def sync_all(self) -> list[str]:
        """Create sync jobs for all enabled subscriptions. Returns job_ids."""
        return self._create_jobs_for_subscriptions(self._repository.list(enabled=True))
