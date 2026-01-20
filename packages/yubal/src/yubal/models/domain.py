"""Domain models for yubal.

These are the public models that represent the output of the library.
"""

from __future__ import annotations

import threading
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CancelToken:
    """Thread-safe cancellation token using threading.Event.

    Tokens are single-use - once cancelled, create a new token for the
    next operation.

    Example:
        >>> token = CancelToken()
        >>> # In worker thread:
        >>> if token.is_cancelled:
        ...     return  # Early exit
        >>> # In main thread:
        >>> token.cancel()  # Signal cancellation
    """

    __slots__ = ("_event",)

    def __init__(self) -> None:
        """Initialize a new cancellation token (not cancelled)."""
        self._event = threading.Event()

    def cancel(self) -> None:
        """Signal that the operation should be cancelled.

        Thread-safe. Can be called from any thread.
        """
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested.

        Thread-safe. Returns True if cancel() has been called.
        """
        return self._event.is_set()


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


class SkipReason(StrEnum):
    """Reason why a track was skipped.

    Used in both extraction and download phases:
    - Extraction: UNSUPPORTED_VIDEO_TYPE, NO_VIDEO_ID
    - Download: FILE_EXISTS
    """

    FILE_EXISTS = "file_exists"
    UNSUPPORTED_VIDEO_TYPE = "unsupported_video_type"
    NO_VIDEO_ID = "no_video_id"


class PhaseStats(BaseModel):
    """Statistics for a processing phase (extraction or download).

    Uses dictionary-based skip reason counts for scalability.
    Adding new skip reasons only requires updating the SkipReason enum.

    Attributes:
        success: Number of successfully processed items.
        failed: Number of failed items.
        skipped_by_reason: Count of skipped items by reason.

    Example:
        >>> stats = PhaseStats(
        ...     success=8,
        ...     failed=1,
        ...     skipped_by_reason={SkipReason.FILE_EXISTS: 2}
        ... )
        >>> stats.skipped  # 2
        >>> stats.total    # 11
        >>> stats.success_rate  # 72.7...
    """

    model_config = ConfigDict(frozen=True)

    success: int = 0
    failed: int = 0
    skipped_by_reason: dict[SkipReason, int] = {}

    @property
    def skipped(self) -> int:
        """Total number of skipped items across all reasons."""
        return sum(self.skipped_by_reason.values())

    @property
    def total(self) -> int:
        """Total items processed (success + failed + skipped)."""
        return self.success + self.failed + self.skipped

    @property
    def success_rate(self) -> float:
        """Success rate as percentage (0.0-100.0). Returns 0.0 if no items."""
        return (self.success / self.total * 100) if self.total > 0 else 0.0


def aggregate_skip_reasons(
    results: list[DownloadResult],
) -> dict[SkipReason, int]:
    """Aggregate skip reasons from download results into a count dictionary.

    This utility extracts skip reason counts from a list of download results,
    useful for logging and stats computation.

    Args:
        results: List of download results to aggregate.

    Returns:
        Dictionary mapping each encountered SkipReason to its count.

    Example:
        >>> reasons = aggregate_skip_reasons(download_results)
        >>> reasons[SkipReason.FILE_EXISTS]  # 5
    """
    counts: dict[SkipReason, int] = {}
    for result in results:
        if result.status == DownloadStatus.SKIPPED and result.skip_reason:
            counts[result.skip_reason] = counts.get(result.skip_reason, 0) + 1
    return counts


class ContentKind(StrEnum):
    """Type of music content (album vs playlist)."""

    ALBUM = "album"
    PLAYLIST = "playlist"


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
        skip_reason: Why the track was skipped (if status is SKIPPED).
    """

    model_config = ConfigDict(frozen=True)

    track: TrackMetadata
    status: DownloadStatus
    output_path: Path | None = None
    error: str | None = None
    video_id_used: str | None = None
    skip_reason: SkipReason | None = None

    @property
    def bitrate(self) -> int | None:
        """Get audio bitrate in kbps from downloaded file."""
        if not self.output_path or not self.output_path.exists():
            return None
        try:
            from mediafile import MediaFile

            audio = MediaFile(self.output_path)
            return audio.bitrate // 1000 if audio.bitrate else None
        except Exception:
            return None


class PlaylistInfo(BaseModel):
    """Information about a playlist.

    Contains metadata about the playlist itself, separate from track data.

    Attributes:
        playlist_id: The YouTube Music playlist ID.
        title: The playlist title/name.
        cover_url: URL to the playlist cover image.
        kind: Whether this is an album or playlist.
        author: Channel/creator name (for playlists).
    """

    model_config = ConfigDict(frozen=True)

    playlist_id: str
    title: str | None = None
    cover_url: str | None = None
    kind: ContentKind = ContentKind.PLAYLIST
    author: str | None = None


class ExtractProgress(BaseModel):
    """Progress update during metadata extraction.

    Yielded by MetadataExtractorService.extract() to report progress.

    Attributes:
        current: Number of tracks successfully extracted so far (1-indexed).
        total: Total number of tracks to process (after limit applied).
        playlist_total: Total number of tracks in the original playlist (before limit).
        skipped_by_reason: Breakdown of skipped tracks by reason.
        track: Extracted track metadata.
        playlist_info: Information about the playlist being extracted.
    """

    model_config = ConfigDict(frozen=True)

    current: int
    total: int
    playlist_total: int
    skipped_by_reason: dict[SkipReason, int] = {}
    track: TrackMetadata
    playlist_info: PlaylistInfo

    @property
    def skipped(self) -> int:
        """Total skipped tracks (for backward compatibility)."""
        return sum(self.skipped_by_reason.values())

    @property
    def unavailable(self) -> int:
        """Tracks without video ID (for backward compatibility)."""
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
        phase: Current phase of the workflow.
        current: Number of items processed in current phase (1-indexed).
        total: Total items in current phase.
        message: Optional status message.
        extract_progress: Extraction progress (when phase is "extracting").
        download_progress: Download progress (when phase is "downloading").
    """

    model_config = ConfigDict(frozen=True)

    phase: Literal["extracting", "downloading", "composing"]
    current: int
    total: int
    message: str | None = None
    extract_progress: ExtractProgress | None = None
    download_progress: DownloadProgress | None = None


class PlaylistDownloadResult(BaseModel):
    """Complete result of a playlist download operation.

    Returned by PlaylistDownloadService after completing a download.

    Attributes:
        playlist_info: Metadata about the downloaded playlist.
        download_results: Results for each track download.
        m3u_path: Path to the generated M3U file (if created).
        cover_path: Path to the saved cover image (if created).
    """

    model_config = ConfigDict(frozen=True)

    playlist_info: PlaylistInfo
    download_results: list[DownloadResult]
    m3u_path: Path | None = None
    cover_path: Path | None = None

    @property
    def success_count(self) -> int:
        """Number of successfully downloaded tracks."""
        return sum(
            1 for r in self.download_results if r.status == DownloadStatus.SUCCESS
        )

    @property
    def skipped_count(self) -> int:
        """Number of skipped tracks (already exist)."""
        return sum(
            1 for r in self.download_results if r.status == DownloadStatus.SKIPPED
        )

    @property
    def failed_count(self) -> int:
        """Number of failed downloads."""
        return sum(
            1 for r in self.download_results if r.status == DownloadStatus.FAILED
        )

    @property
    def download_stats(self) -> PhaseStats:
        """Compute download phase statistics with skip reason breakdown."""
        return PhaseStats(
            success=self.success_count,
            failed=self.failed_count,
            skipped_by_reason=aggregate_skip_reasons(self.download_results),
        )
