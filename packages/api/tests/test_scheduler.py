"""Tests for the scheduler service."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from yubal_api.services.scheduler import Scheduler


@pytest.fixture
def scheduler(mock_settings: MagicMock) -> Scheduler:
    """Create scheduler with mocked dependencies."""
    repository = MagicMock()
    job_executor = MagicMock()
    return Scheduler(repository, job_executor, mock_settings)


class TestCronExpression:
    """Tests for cron_expression property."""

    def test_returns_cron_from_settings(self, scheduler: Scheduler) -> None:
        """Should return cron expression from settings."""
        assert scheduler.cron_expression == "0 */6 * * *"


class TestGetNextRunTime:
    """Tests for _get_next_run_time calculation."""

    def test_calculates_next_run_in_utc(
        self, scheduler: Scheduler, mock_settings: MagicMock
    ) -> None:
        """Should calculate next run time and return in UTC."""
        mock_settings.sync_cron = "0 * * * *"  # Every hour
        mock_settings.timezone = ZoneInfo("UTC")

        next_run = scheduler._get_next_run_time()

        assert next_run.tzinfo == UTC
        assert next_run > datetime.now(UTC)
        # Should be at minute 0 (top of hour)
        assert next_run.minute == 0
        assert next_run.second == 0

    def test_respects_configured_timezone(
        self, scheduler: Scheduler, mock_settings: MagicMock
    ) -> None:
        """Should evaluate cron in configured timezone."""
        # Set timezone to UTC+1
        tz = ZoneInfo("Europe/Paris")
        mock_settings.timezone = tz
        mock_settings.sync_cron = "0 */6 * * *"  # Every 6 hours

        next_run = scheduler._get_next_run_time()

        # Result should be in UTC
        assert next_run.tzinfo == UTC

        # Convert to local timezone to verify cron was evaluated correctly
        next_run_local = next_run.astimezone(tz)
        # Should be at hour 0, 6, 12, or 18 in local time
        assert next_run_local.hour in (0, 6, 12, 18)
        assert next_run_local.minute == 0

    def test_next_run_is_in_future(
        self, scheduler: Scheduler, mock_settings: MagicMock
    ) -> None:
        """Should always return a future time."""
        mock_settings.sync_cron = "* * * * *"  # Every minute
        mock_settings.timezone = ZoneInfo("UTC")

        next_run = scheduler._get_next_run_time()

        assert next_run > datetime.now(UTC)

    def test_different_timezones_produce_different_utc_times(
        self, mock_settings: MagicMock
    ) -> None:
        """Same cron in different timezones should produce different UTC times."""
        repository = MagicMock()
        job_executor = MagicMock()

        # Scheduler with UTC
        mock_settings.timezone = ZoneInfo("UTC")
        mock_settings.sync_cron = "0 12 * * *"  # Noon
        scheduler_utc = Scheduler(repository, job_executor, mock_settings)
        next_utc = scheduler_utc._get_next_run_time()

        # Scheduler with Tokyo (UTC+9)
        mock_settings_tokyo = MagicMock()
        mock_settings_tokyo.sync_enabled = True
        mock_settings_tokyo.sync_cron = "0 12 * * *"  # Noon
        mock_settings_tokyo.timezone = ZoneInfo("Asia/Tokyo")
        scheduler_tokyo = Scheduler(repository, job_executor, mock_settings_tokyo)
        next_tokyo = scheduler_tokyo._get_next_run_time()

        # Noon in Tokyo is 3am UTC, noon in UTC is 12pm UTC
        # They should differ by ~9 hours (depending on current time)
        diff = abs((next_utc - next_tokyo).total_seconds())
        # Allow for day wraparound - diff should be ~9h or ~15h (24-9)
        assert diff in range(8 * 3600, 10 * 3600) or diff in range(14 * 3600, 16 * 3600)


class TestSchedulerProperties:
    """Tests for scheduler properties."""

    def test_enabled_returns_settings_value(
        self, scheduler: Scheduler, mock_settings: MagicMock
    ) -> None:
        """Should return sync_enabled from settings."""
        mock_settings.sync_enabled = True
        assert scheduler.enabled is True

        mock_settings.sync_enabled = False
        assert scheduler.enabled is False

    def test_is_running_false_when_not_started(self, scheduler: Scheduler) -> None:
        """Should be False when scheduler hasn't been started."""
        assert scheduler.is_running is False

    def test_next_run_at_none_when_not_started(self, scheduler: Scheduler) -> None:
        """Should be None when scheduler hasn't been started."""
        assert scheduler.next_run_at is None
