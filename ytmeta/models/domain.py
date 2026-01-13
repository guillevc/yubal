"""Domain models for ytmeta.

These are the public models that represent the output of the library.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class VideoType(StrEnum):
    """YouTube Music video types.

    Maps to ytmusicapi.models.content.enums.VideoType values.
    """

    ATV = "MUSIC_VIDEO_TYPE_ATV"  # Audio Track Video (album version)
    OMV = "MUSIC_VIDEO_TYPE_OMV"  # Official Music Video
    OFFICIAL_SOURCE_MUSIC = "MUSIC_VIDEO_TYPE_OFFICIAL_SOURCE_MUSIC"  # Official source
    UGC = "MUSIC_VIDEO_TYPE_UGC"  # User Generated Content


class DownloadStatus(StrEnum):
    """Status of a download operation."""

    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


class TrackMetadata(BaseModel):
    """Metadata for a single track."""

    omv_video_id: str | None = None
    atv_video_id: str | None = None
    title: str
    artists: list[str]
    album: str
    album_artists: list[str]
    track_number: int | None = None
    total_tracks: int | None = None
    year: str | None = None
    cover_url: str | None = None
    video_type: VideoType | None = None

    @property
    def artist(self) -> str:
        """Joined artists for metadata embedding."""
        return "; ".join(self.artists)

    @property
    def album_artist(self) -> str:
        """Joined album artists for metadata embedding."""
        return "; ".join(self.album_artists)

    @property
    def primary_album_artist(self) -> str:
        """First album artist for path construction."""
        return self.album_artists[0] if self.album_artists else "Unknown Artist"


class DownloadResult(BaseModel):
    """Result of a single track download.

    Attributes:
        track: The track metadata that was downloaded.
        status: The download status.
        output_path: Path to the downloaded file (if successful).
        error: Error message (if failed).
        video_id_used: The video ID that was used for download.
    """

    model_config = ConfigDict(frozen=True)

    track: TrackMetadata
    status: DownloadStatus
    output_path: Path | None = None
    error: str | None = None
    video_id_used: str | None = None


class PlaylistInfo(BaseModel):
    """Information about a playlist.

    Contains metadata about the playlist itself, separate from track data.

    Attributes:
        playlist_id: The YouTube Music playlist ID.
        title: The playlist title/name.
    """

    model_config = ConfigDict(frozen=True)

    playlist_id: str
    title: str | None = None


class ExtractProgress(BaseModel):
    """Progress update during metadata extraction.

    Yielded by MetadataExtractorService.extract() to report progress.

    Attributes:
        current: Number of tracks successfully extracted so far (1-indexed).
        total: Total number of tracks in the original playlist.
        skipped: Number of tracks skipped so far (unsupported video types).
        unavailable: Number of tracks without videoId (not available/not music).
        track: Extracted track metadata.
        playlist_info: Information about the playlist being extracted.
    """

    model_config = ConfigDict(frozen=True)

    current: int
    total: int
    skipped: int
    unavailable: int
    track: TrackMetadata
    playlist_info: PlaylistInfo


class DownloadProgress(BaseModel):
    """Progress update during track download.

    Yielded by DownloadService.download_tracks() to report progress.

    Attributes:
        current: Number of tracks processed so far (1-indexed).
        total: Total number of tracks to download.
        result: Download result for the current track.
    """

    model_config = ConfigDict(frozen=True)

    current: int
    total: int
    result: DownloadResult
