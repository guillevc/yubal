"""Application settings using pydantic-settings."""

import tempfile
from datetime import tzinfo
from functools import lru_cache
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from yubal_api.core.types import AudioFormat


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
    library_dir: Path = Field(description="Music library")
    ytdlp_dir: Path = Field(description="yt-dlp config dir")

    # Server settings
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Log level")

    # Audio settings
    audio_format: AudioFormat = Field(default="opus", description="Audio format")
    audio_quality: str = Field(default="0", description="Audio quality (0 = best)")

    # Temp directory
    temp_dir: Path = Field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "yubal",
        description="Temp directory for downloads",
    )

    # CORS settings
    cors_origins: list[str] = Field(default=["*"], description="Allowed CORS origins")

    # Timezone
    tz: str = Field(default="UTC", description="Timezone for timestamps")

    @model_validator(mode="before")
    @classmethod
    def set_path_defaults(cls, data: Any) -> Any:
        """Set path defaults based on root before validation."""
        if not isinstance(data, dict):
            return data
        root = data.get("root")
        if root:
            root = Path(root) if isinstance(root, str) else root
            if not data.get("library_dir"):
                data["library_dir"] = root / "data"
            if not data.get("ytdlp_dir"):
                data["ytdlp_dir"] = root / "ytdlp"
        return data

    @property
    def timezone(self) -> tzinfo:
        return ZoneInfo(self.tz)

    @property
    def cookies_file(self) -> Path:
        return self.ytdlp_dir / "cookies.txt"

    @property
    def playlists_dir(self) -> Path:
        return self.library_dir / "Playlists"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()  # type: ignore[call-arg]
