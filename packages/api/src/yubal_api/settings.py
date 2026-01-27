"""Application settings using pydantic-settings."""

import tempfile
from datetime import tzinfo
from functools import cache
from pathlib import Path
from typing import Annotated, Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BeforeValidator, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from yubal import AudioCodec

LogLevel = Annotated[
    Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    BeforeValidator(lambda v: v.upper() if isinstance(v, str) else v),
]


def _validate_timezone(v: str) -> str:
    """Validate timezone string by attempting to create ZoneInfo."""
    if isinstance(v, str):
        try:
            ZoneInfo(v)
        except KeyError as e:
            raise ValueError(f"Invalid timezone: {v}") from e
    return v


Timezone = Annotated[str, BeforeValidator(_validate_timezone)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="YUBAL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Project root (required, set via YUBAL_ROOT)
    root: Path = Field(description="Project root directory")

    # Path settings (default to root-relative paths)
    data: Path = Field(description="Music library")
    config: Path = Field(description="Config directory")

    # Server settings
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: LogLevel = Field(default="INFO", description="Log level")

    # Audio settings
    audio_format: AudioCodec = Field(
        default=AudioCodec.OPUS, description="Audio format"
    )
    audio_quality: str = Field(default="0", description="Audio quality (0 = best)")

    # Lyrics settings
    fetch_lyrics: bool = Field(default=True, description="Fetch lyrics from lrclib.net")

    # Temp directory
    temp: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "yubal",
        description="Temp directory for downloads",
    )

    # CORS settings
    cors_origins: list[str] = Field(default=["*"], description="Allowed CORS origins")

    # Scheduler settings
    sync_enabled: bool = Field(
        default=True, description="Enable playlist sync scheduler"
    )
    sync_interval_minutes: int = Field(
        default=60,
        ge=5,
        le=10080,
        description="Sync interval in minutes (5 min to 1 week)",
    )

    # Timezone
    tz: Timezone = Field(default="UTC", description="Timezone for timestamps")

    @model_validator(mode="before")
    @classmethod
    def set_path_defaults(cls, data: Any) -> Any:
        """Set path defaults based on root before validation."""
        if not isinstance(data, dict):
            return data
        root = data.get("root")
        if not root:
            raise ValueError("YUBAL_ROOT environment variable is required")
        root = Path(root) if isinstance(root, str) else root
        if not data.get("data"):
            data["data"] = root / "data"
        if not data.get("config"):
            data["config"] = root / "config"
        return data

    @property
    def timezone(self) -> tzinfo:
        return ZoneInfo(self.tz)

    @property
    def ytdlp_dir(self) -> Path:
        return self.config / "ytdlp"

    @property
    def cookies_file(self) -> Path:
        return self.ytdlp_dir / "cookies.txt"


@cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[call-arg]
