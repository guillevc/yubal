"""Sync operation schemas."""

from pydantic import BaseModel

from yubal.core import AlbumInfo


class SyncRequest(BaseModel):
    """Request schema for sync operation."""

    url: str  # YouTube Music URL
    audio_format: str = "mp3"


class SyncResponse(BaseModel):
    """Response schema for sync operation result."""

    success: bool
    album: AlbumInfo | None = None
    destination: str | None = None
    track_count: int = 0
    error: str | None = None
