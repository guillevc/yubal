"""Test fixtures and configuration for yubal-api tests.

This module provides shared fixtures organized into:
- Database fixtures: In-memory SQLite for repository tests
- Mock fixtures: Common mocks for settings and dependencies
- Factory fixtures: Builders for test data
"""

from collections.abc import Callable, Generator
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine
from yubal_api.db.repository import SubscriptionRepository

# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    """Create in-memory SQLite engine for tests."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine


@pytest.fixture
def repository(engine: Engine) -> SubscriptionRepository:
    """Create repository with test engine."""
    return SubscriptionRepository(engine)


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings with default values."""
    settings = MagicMock()
    settings.scheduler_enabled = True
    settings.scheduler_cron = "0 0 * * *"
    settings.timezone = ZoneInfo("UTC")
    return settings


# =============================================================================
# Time Utilities
# =============================================================================


class MockClock:
    """Mock clock for deterministic time-based testing.

    Usage:
        clock = MockClock()
        clock.advance(60)  # Advance by 60 seconds
        clock.set(datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC))
    """

    def __init__(self, initial: datetime | None = None) -> None:
        self._time = initial or datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self._time

    def advance(self, seconds: int) -> None:
        """Advance the clock by the specified seconds."""
        self._time += timedelta(seconds=seconds)

    def set(self, time: datetime) -> None:
        """Set the clock to a specific time."""
        self._time = time


class MockIdGenerator:
    """Mock ID generator for deterministic ID generation.

    Usage:
        gen = MockIdGenerator(prefix="job")
        gen()  # Returns "job-0001"
        gen()  # Returns "job-0002"
    """

    def __init__(self, prefix: str = "job") -> None:
        self._counter = 0
        self._prefix = prefix

    def __call__(self) -> str:
        self._counter += 1
        return f"{self._prefix}-{self._counter:04d}"

    def reset(self) -> None:
        """Reset the counter."""
        self._counter = 0


@pytest.fixture
def clock() -> MockClock:
    """Provide a mock clock."""
    return MockClock()


@pytest.fixture
def id_generator() -> MockIdGenerator:
    """Provide a mock ID generator."""
    return MockIdGenerator()


# =============================================================================
# Factory Fixtures
# =============================================================================


@pytest.fixture
def make_subscription() -> Callable[..., dict]:
    """Factory for creating subscription data dicts."""
    from yubal_api.db.subscription import SubscriptionType

    def _make_subscription(
        url: str = "https://music.youtube.com/playlist?list=PLtest",
        name: str = "Test Playlist",
        type: SubscriptionType = SubscriptionType.PLAYLIST,
        enabled: bool = True,
    ) -> dict:
        return {
            "type": type,
            "url": url,
            "name": name,
            "enabled": enabled,
        }

    return _make_subscription
