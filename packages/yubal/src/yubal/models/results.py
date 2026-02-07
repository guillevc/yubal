"""Download result models and statistics."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from yubal.models.enums import DownloadStatus, SkipReason
from yubal.models.track import PlaylistInfo, TrackMetadata


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
    skipped_by_reason: dict[SkipReason, int] = Field(default_factory=dict)

    @property
    def skipped(self) -> int:
        """Total number of skipped items across all reasons."""
        return sum(self.skipped_by_reason.values())

    @property
    def total(self) -> int:
        """Total items processed (success + failed + skipped)."""
        return self.success + self.failed + self.skipped


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
