"""Progress tracking models for extraction and download phases."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from yubal.models.enums import SkipReason
from yubal.models.results import DownloadResult
from yubal.models.track import PlaylistInfo, TrackMetadata


class ExtractProgress(BaseModel):
    """Progress update during metadata extraction.

    Yielded by MetadataExtractorService.extract() to report progress.

    Attributes:
        current: Number of tracks successfully extracted so far (1-indexed).
        total: Total number of tracks to process (after limit applied).
        playlist_total: Total number of tracks in the original playlist (before limit).
        skipped_by_reason: Breakdown of skipped tracks by reason.
        track: Extracted track metadata, or None if track was skipped.
        playlist_info: Information about the playlist being extracted.
    """

    model_config = ConfigDict(frozen=True)

    current: int
    total: int
    playlist_total: int
    skipped_by_reason: dict[SkipReason, int] = Field(default_factory=dict)
    track: TrackMetadata | None
    playlist_info: PlaylistInfo

    @property
    def skipped(self) -> int:
        """Total skipped tracks across all skip reasons."""
        return sum(self.skipped_by_reason.values())

    @property
    def unavailable(self) -> int:
        """Tracks skipped due to missing video ID."""
        return self.skipped_by_reason.get(SkipReason.NO_VIDEO_ID, 0)


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


class PlaylistProgress(BaseModel):
    """Progress update during playlist download.

    Unified progress for the entire playlist workflow, yielded by
    PlaylistDownloadService.download_playlist().

    Attributes:
        phase: Current phase of the workflow (extracting, downloading,
            composing, or normalizing).
        current: Number of items processed in current phase (1-indexed).
        total: Total items in current phase.
        message: Optional status message.
        extract_progress: Extraction progress (when phase is "extracting").
        download_progress: Download progress (when phase is "downloading").
    """

    model_config = ConfigDict(frozen=True)

    phase: Literal["extracting", "downloading", "composing", "normalizing"]
    current: int
    total: int
    message: str | None = None
    extract_progress: ExtractProgress | None = None
    download_progress: DownloadProgress | None = None
