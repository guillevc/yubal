"""Tests for application settings."""

import os
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from yubal_api.settings import Settings

# Common test paths
TEST_ROOT = Path("/tmp/test")
TEST_DATA = Path("/tmp/test/data")
TEST_CONFIG = Path("/tmp/test/config")


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Isolate tests from .env file and shell environment."""
    # Clear all YUBAL_* env vars
    for key in list(os.environ.keys()):
        if key.startswith("YUBAL_"):
            monkeypatch.delenv(key, raising=False)
    # Change to temp dir so Settings won't find .env file
    monkeypatch.chdir(tmp_path)


def _create_settings(**kwargs: Any) -> Settings:
    """Helper to create Settings with defaults for required fields."""
    defaults: dict[str, Any] = {
        "root": TEST_ROOT,
        "data": TEST_DATA,
        "config": TEST_CONFIG,
    }
    defaults.update(kwargs)
    return Settings(**defaults)


class TestLogLevel:
    """Tests for LogLevel type validation."""

    # Valid log levels
    @pytest.mark.parametrize(
        "level",
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    def test_accepts_valid_uppercase_levels(self, level: str) -> None:
        """Should accept valid log levels in uppercase."""
        settings = _create_settings(log_level=level)
        assert settings.log_level == level

    # Case-insensitive input
    @pytest.mark.parametrize(
        ("input_level", "expected"),
        [
            ("debug", "DEBUG"),
            ("info", "INFO"),
            ("warning", "WARNING"),
            ("error", "ERROR"),
            ("critical", "CRITICAL"),
        ],
    )
    def test_normalizes_lowercase_to_uppercase(
        self, input_level: str, expected: str
    ) -> None:
        """Should normalize lowercase input to uppercase."""
        settings = _create_settings(log_level=input_level)
        assert settings.log_level == expected

    @pytest.mark.parametrize(
        ("input_level", "expected"),
        [
            ("Debug", "DEBUG"),
            ("Info", "INFO"),
            ("WaRnInG", "WARNING"),
            ("ErRoR", "ERROR"),
        ],
    )
    def test_normalizes_mixed_case_to_uppercase(
        self, input_level: str, expected: str
    ) -> None:
        """Should normalize mixed case input to uppercase."""
        settings = _create_settings(log_level=input_level)
        assert settings.log_level == expected

    # Invalid log levels
    @pytest.mark.parametrize(
        "invalid_level",
        ["VERBOSE", "TRACE", "WARN", "FATAL", "OFF", "ALL", "invalid", ""],
    )
    def test_rejects_invalid_levels(self, invalid_level: str) -> None:
        """Should reject invalid log levels."""
        with pytest.raises(ValidationError) as exc_info:
            _create_settings(log_level=invalid_level)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("log_level",)

    def test_default_log_level(self) -> None:
        """Should use INFO as default log level."""
        settings = _create_settings()
        assert settings.log_level == "INFO"


class TestRootRequired:
    """Tests for root directory requirement."""

    def test_raises_when_root_missing(self) -> None:
        """Should raise error when root is not provided."""
        with pytest.raises(
            ValidationError, match="YUBAL_ROOT environment variable is required"
        ):
            Settings(data=TEST_DATA, config=TEST_CONFIG)  # type: ignore[call-arg]

    def test_accepts_root_as_string(self) -> None:
        """Should accept root as string and convert to Path."""
        settings = Settings(
            root="/tmp/test",  # type: ignore[arg-type]
            data=TEST_DATA,
            config=TEST_CONFIG,
        )
        assert settings.root == Path("/tmp/test")

    def test_accepts_root_as_path(self) -> None:
        """Should accept root as Path."""
        settings = _create_settings()
        assert settings.root == TEST_ROOT


class TestPathDefaults:
    """Tests for path default values based on root."""

    def test_data_defaults_to_root_data(self) -> None:
        """Should default data to root/data."""
        settings = Settings(
            root=TEST_ROOT,
            config=TEST_CONFIG,
        )  # type: ignore[call-arg]
        assert settings.data == Path("/tmp/test/data")

    def test_config_defaults_to_root_config(self) -> None:
        """Should default config to root/config."""
        settings = Settings(
            root=TEST_ROOT,
            data=TEST_DATA,
        )  # type: ignore[call-arg]
        assert settings.config == Path("/tmp/test/config")

    def test_data_can_be_overridden(self) -> None:
        """Should allow data to be explicitly set."""
        custom_data = Path("/custom/data")
        settings = _create_settings(data=custom_data)
        assert settings.data == custom_data

    def test_config_can_be_overridden(self) -> None:
        """Should allow config to be explicitly set."""
        custom_config = Path("/custom/config")
        settings = _create_settings(config=custom_config)
        assert settings.config == custom_config


class TestTimezone:
    """Tests for timezone validation."""

    def test_valid_timezone(self) -> None:
        """Should accept valid timezone."""
        settings = _create_settings(tz="America/New_York")
        assert settings.tz == "America/New_York"
        assert str(settings.timezone) == "America/New_York"

    def test_utc_timezone(self) -> None:
        """Should accept UTC timezone."""
        settings = _create_settings(tz="UTC")
        assert settings.tz == "UTC"
        assert str(settings.timezone) == "UTC"

    def test_invalid_timezone_raises_on_construction(self) -> None:
        """Should raise ValidationError at construction for invalid timezone."""
        with pytest.raises(ValidationError) as exc_info:
            _create_settings(tz="Invalid/Timezone")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("tz",)


class TestCronExpression:
    """Tests for cron expression validation."""

    @pytest.mark.parametrize(
        "cron",
        [
            "0 * * * *",  # Every hour
            "*/30 * * * *",  # Every 30 minutes
            "0 */6 * * *",  # Every 6 hours
            "0 3 * * *",  # Daily at 3am
            "0 0 * * 0",  # Weekly on Sunday
            "0 0 1 * *",  # Monthly on 1st
        ],
    )
    def test_accepts_valid_cron_expressions(self, cron: str) -> None:
        """Should accept valid cron expressions."""
        settings = _create_settings(scheduler_cron=cron)
        assert settings.scheduler_cron == cron

    @pytest.mark.parametrize(
        "invalid_cron",
        [
            "invalid",
            "* * *",  # Too few fields
            "60 * * * *",  # Invalid minute (0-59)
            "* 25 * * *",  # Invalid hour (0-23)
            "",
        ],
    )
    def test_rejects_invalid_cron_expressions(self, invalid_cron: str) -> None:
        """Should reject invalid cron expressions."""
        with pytest.raises(ValidationError) as exc_info:
            _create_settings(scheduler_cron=invalid_cron)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("scheduler_cron",)

    def test_default_cron_expression(self) -> None:
        """Should use daily at midnight as default."""
        settings = _create_settings()
        assert settings.scheduler_cron == "0 0 * * *"
