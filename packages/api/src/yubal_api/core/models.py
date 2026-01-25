"""Core domain models for the API."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from yubal import AudioCodec, ContentKind, PhaseStats

from yubal_api.core.enums import JobStatus


class AlbumInfo(BaseModel):
    """Information about an album/playlist."""

    title: str
    artist: str
    year: int | None = None
    track_count: int
    playlist_id: str = ""
    url: str = ""
    thumbnail_url: str | None = None
    audio_codec: str | None = None  # e.g. "opus", "mp3"
    audio_bitrate: int | None = None  # kbps, e.g. 128
    kind: ContentKind = ContentKind.PLAYLIST


class Job(BaseModel):
    """A background sync job."""

    model_config = ConfigDict(validate_assignment=True)

    id: str
    url: str
    audio_format: AudioCodec = AudioCodec.OPUS
    max_items: int | None = None
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    album_info: AlbumInfo | None = None
    download_stats: PhaseStats | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
