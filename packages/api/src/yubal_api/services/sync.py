"""Content synchronization service adapting yubal library for the API.

This module provides a thin adapter over yubal's content downloader,
translating yubal's progress model to the API's job progress system.
Handles playlists, albums, and single tracks.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from yubal import (
    AudioCodec,
    CancellationError,
    CancelToken,
    DownloadConfig,
    DownloadStatus,
    PhaseStats,
    PlaylistDownloadConfig,
    PlaylistProgress,
    TrackMetadata,
    create_playlist_downloader,
)
from yubal.models.enums import ContentKind
from yubal.models.track import PlaylistInfo
from yubal.services.pipeline import PlaylistDownloadService

from yubal_api.domain.enums import ProgressStep
from yubal_api.domain.job import ContentInfo

logger = logging.getLogger(__name__)

# Type alias for the progress callback signature
ProgressCallback = Callable[
    [ProgressStep, str, float | None, dict[str, Any] | None], None
]


# -----------------------------------------------------------------------------
# Progress Phase Configuration
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PhaseRange:
    """Progress percentage boundaries for a workflow phase."""

    start: float
    end: float

    def interpolate(self, current: int, total: int) -> float:
        """Map item progress to overall percentage within this phase."""
        if total == 0:
            return self.start
        ratio = current / total
        return self.start + ratio * (self.end - self.start)


# Extraction: 0-10%, Download: 10-85%, Compose: 85-90%, Normalize: 90-100%
PHASE_RANGES: dict[str, PhaseRange] = {
    "extracting": PhaseRange(0.0, 10.0),
    "downloading": PhaseRange(10.0, 85.0),
    "composing": PhaseRange(85.0, 90.0),
    "normalizing": PhaseRange(90.0, 100.0),
}

PHASE_TO_STEP: dict[str, ProgressStep] = {
    "extracting": ProgressStep.FETCHING_INFO,
    "downloading": ProgressStep.DOWNLOADING,
    "composing": ProgressStep.IMPORTING,
    "normalizing": ProgressStep.IMPORTING,
}


def _phase_to_step(phase: str) -> ProgressStep:
    """Convert yubal phase name to API progress step. Raises on unknown phase."""
    try:
        return PHASE_TO_STEP[phase]
    except KeyError:
        raise ValueError(f"Unknown workflow phase: {phase!r}") from None


def _compute_progress(phase: str, current: int, total: int) -> float:
    """Calculate overall progress percentage for current phase position."""
    phase_range = PHASE_RANGES.get(phase)
    if phase_range is None:
        return 0.0
    return phase_range.interpolate(current, total)


# -----------------------------------------------------------------------------
# Result Types
# -----------------------------------------------------------------------------


@dataclass(slots=True)
class SyncResult:
    """Outcome of a content sync operation.

    Attributes:
        success: Whether the operation completed successfully.
        content_info: Metadata about the synced content (if extraction succeeded).
        download_stats: Statistics from the download phase.
        destination: Path to the directory containing downloaded files.
        error: Error message if the operation failed.
    """

    success: bool
    content_info: ContentInfo | None = None
    download_stats: PhaseStats | None = None
    destination: str | None = None
    error: str | None = None


# -----------------------------------------------------------------------------
# Content Info Mapping
# -----------------------------------------------------------------------------


def build_content_info(
    playlist: PlaylistInfo,
    tracks: list[TrackMetadata],
    url: str,
    audio_format: str,
) -> ContentInfo:
    """Convert yubal extraction data to API ContentInfo model.

    Args:
        playlist: Playlist/album metadata from yubal.
        tracks: List of extracted track metadata.
        url: Original source URL.
        audio_format: Target audio format (opus, mp3, m4a).

    Returns:
        ContentInfo model suitable for API responses.
    """
    first_track = tracks[0] if tracks else None

    # Only include year for albums, not user playlists
    year = _extract_year(playlist, first_track)

    # Use channel name for playlists, album artist for albums
    artist = _determine_artist(playlist, first_track)

    return ContentInfo(
        title=playlist.title or "Unknown",
        artist=artist,
        year=year,
        track_count=len(tracks),
        playlist_id=playlist.playlist_id,
        url=url,
        thumbnail_url=playlist.cover_url
        or (first_track.cover_url if first_track else None),
        audio_codec=audio_format.upper(),
        audio_bitrate=None,  # Set after first successful download
        kind=playlist.kind.value,
    )


def build_early_content_info(
    playlist: PlaylistInfo,
    url: str,
    audio_format: str,
) -> ContentInfo:
    """Build preliminary ContentInfo from playlist metadata only.

    Called immediately when playlist_info becomes available for early UI feedback.
    Fields requiring track data use placeholder values.
    """
    return ContentInfo(
        title=playlist.title or "Unknown",
        artist=playlist.author or "Unknown Artist",
        year=None,
        track_count=None,  # Updated when extraction completes
        playlist_id=playlist.playlist_id,
        url=url,
        thumbnail_url=playlist.cover_url,
        audio_codec=audio_format.upper(),
        audio_bitrate=None,
        kind=playlist.kind.value,
    )


def _extract_year(
    playlist: PlaylistInfo, first_track: TrackMetadata | None
) -> int | None:
    """Extract release year for albums only."""
    if playlist.kind == ContentKind.PLAYLIST:
        return None
    if first_track is None or not first_track.year:
        return None
    try:
        return int(first_track.year)
    except ValueError:
        return None


def _determine_artist(playlist: PlaylistInfo, first_track: TrackMetadata | None) -> str:
    """Determine the display artist based on content kind."""
    if playlist.kind == ContentKind.PLAYLIST and playlist.author:
        return playlist.author
    if first_track:
        return first_track.primary_album_artist
    return "Various Artists"


# -----------------------------------------------------------------------------
# Message Formatting
# -----------------------------------------------------------------------------


def _format_extraction_message(progress: PlaylistProgress) -> str:
    """Format user-facing message for extraction phase."""
    if progress.extract_progress:
        ep = progress.extract_progress
        title = ep.track.title if ep.track else "skipped"
        return f"Extracted {ep.current}/{ep.total}: {title}"
    return f"Extracting {progress.current}/{progress.total}..."


def _format_download_message(progress: PlaylistProgress) -> str:
    """Format user-facing message for download phase."""
    if not progress.download_progress:
        return f"Downloading {progress.current}/{progress.total}..."

    dp = progress.download_progress
    result = dp.result

    status_text = _download_status_text(result.status, result.skip_reason)
    return f"[{dp.current}/{dp.total}] {result.track.title}: {status_text}"


def _download_status_text(status: DownloadStatus, skip_reason: Any) -> str:
    """Convert download status to human-readable text."""
    if status == DownloadStatus.SUCCESS:
        return "downloaded"
    if status == DownloadStatus.SKIPPED and skip_reason:
        return f"skipped ({skip_reason.label})"
    return status.value


# -----------------------------------------------------------------------------
# Sync Service
# -----------------------------------------------------------------------------


@dataclass
class SyncService:
    """Adapter for yubal's content downloader with API-compatible progress.

    This service wraps yubal's PlaylistDownloadService to provide:
    - Progress callbacks compatible with the job system
    - Phase-aware progress percentage calculation
    - Content metadata extraction for job updates

    Handles playlists, albums, and single tracks.

    Example:
        service = SyncService(Path("/downloads"), "opus")
        result = service.run(
            url="https://music.youtube.com/playlist?list=...",
            on_progress=lambda step, msg, pct, details: print(f"{step}: {msg}"),
            cancel_token=CancelToken(),
        )
    """

    base_path: Path
    audio_format: str = "opus"
    cookies_path: Path | None = None
    fetch_lyrics: bool = True
    apply_replaygain: bool = False
    _codec: AudioCodec = field(init=False)

    def __post_init__(self) -> None:
        self._codec = AudioCodec(self.audio_format)

    def run(
        self,
        url: str,
        on_progress: ProgressCallback | None,
        cancel_token: CancelToken,
        max_items: int | None = None,
    ) -> SyncResult:
        """Execute the full extraction and download workflow.

        Progress phases:
        - 0-10%: Extracting metadata from source
        - 10-90%: Downloading and transcoding tracks
        - 90-100%: Generating playlist files (M3U, cover art)

        Args:
            url: YouTube Music album or playlist URL.
            on_progress: Optional callback for progress updates.
            cancel_token: Token for cooperative cancellation.
            max_items: Maximum number of tracks to download (None for all).

        Returns:
            SyncResult with operation outcome and metadata.
        """
        workflow = _SyncWorkflow(
            url=url,
            on_progress=on_progress,
            cancel_token=cancel_token,
            max_items=max_items,
            base_path=self.base_path,
            codec=self._codec,
            audio_format=self.audio_format,
            cookies_path=self.cookies_path,
            fetch_lyrics=self.fetch_lyrics,
            apply_replaygain=self.apply_replaygain,
        )
        return workflow.execute()


# -----------------------------------------------------------------------------
# Workflow Implementation
# -----------------------------------------------------------------------------


@dataclass
class _SyncWorkflow:
    """Internal workflow state and execution logic.

    Separated from the service class to keep state management isolated
    and make the execution flow clearer.
    """

    url: str
    on_progress: ProgressCallback | None
    cancel_token: CancelToken
    max_items: int | None
    base_path: Path
    codec: AudioCodec
    audio_format: str
    cookies_path: Path | None
    fetch_lyrics: bool
    apply_replaygain: bool

    # Workflow state
    content_info: ContentInfo | None = field(default=None, init=False)
    playlist_info: PlaylistInfo | None = field(default=None, init=False)
    tracks: list[TrackMetadata] = field(default_factory=list, init=False)
    previous_phase: str | None = field(default=None, init=False)

    def execute(self) -> SyncResult:
        """Run the complete sync workflow."""
        try:
            return self._run_download_workflow()
        except CancellationError:
            logger.info("Download cancelled", extra={"status": "failed"})
            return SyncResult(
                success=False,
                content_info=self.content_info,
                error="Cancelled",
            )
        except Exception as e:
            logger.exception("Sync failed: %s", e)
            self._emit(ProgressStep.FAILED, str(e))
            return SyncResult(
                success=False,
                content_info=self.content_info,
                error=str(e),
            )

    def _run_download_workflow(self) -> SyncResult:
        """Execute the download workflow phases."""
        downloader = self._create_downloader()

        self._emit(ProgressStep.FETCHING_INFO, "Starting...", 0.0)

        for progress in downloader.download_playlist(self.url, self.cancel_token):
            self._handle_progress(progress)

        return self._build_result(downloader)

    def _create_downloader(self) -> PlaylistDownloadService:
        """Create configured content downloader instance."""
        config = PlaylistDownloadConfig(
            download=DownloadConfig(
                base_path=self.base_path,
                codec=self.codec,
                quiet=True,
                fetch_lyrics=self.fetch_lyrics,
            ),
            generate_m3u=True,
            save_cover=True,
            max_items=self.max_items,
            apply_replaygain=self.apply_replaygain,
        )
        return create_playlist_downloader(config, cookies_path=self.cookies_path)

    def _handle_progress(self, progress: PlaylistProgress) -> None:
        """Route progress update to appropriate phase handler."""
        step = _phase_to_step(progress.phase)
        percent = _compute_progress(progress.phase, progress.current, progress.total)

        # Emit content_info on phase transition from extraction
        self._check_extraction_complete(progress)
        self.previous_phase = progress.phase

        if progress.phase == "extracting":
            self._handle_extraction(progress, step, percent)
        elif progress.phase == "downloading":
            self._handle_download(progress, step, percent)
        elif progress.phase == "composing":
            self._emit(
                step, progress.message or "Generating playlist files...", percent
            )

    def _check_extraction_complete(self, progress: PlaylistProgress) -> None:
        """Update content_info when transitioning out of extraction phase.

        This handles the case where some tracks are skipped (UGC videos)
        and the extraction current count never equals total.
        """
        is_leaving_extraction = (
            self.previous_phase == "extracting" and progress.phase != "extracting"
        )
        # Update content_info with track data if we have tracks but haven't updated yet
        should_update = (
            is_leaving_extraction
            and self.playlist_info is not None
            and self.tracks
            and (self.content_info is None or self.content_info.track_count is None)
        )

        if should_update:
            self._update_content_info_complete()

    def _handle_extraction(
        self,
        progress: PlaylistProgress,
        step: ProgressStep,
        percent: float,
    ) -> None:
        """Process extraction phase progress update."""
        if progress.extract_progress:
            if progress.extract_progress.track is not None:
                self.tracks.append(progress.extract_progress.track)
            self.playlist_info = progress.extract_progress.playlist_info

        # Emit early content_info on first progress with playlist_info
        if self.playlist_info is not None and self.content_info is None:
            self._emit_early_content_info()

        self._emit(step, _format_extraction_message(progress), percent)

        # Update content_info when extraction completes
        extraction_complete = (
            progress.current == progress.total
            and self.playlist_info is not None
            and self.tracks
        )
        if extraction_complete:
            self._update_content_info_complete()

    def _emit_early_content_info(self) -> None:
        """Emit preliminary content_info when playlist_info first becomes available."""
        if self.content_info is not None or self.playlist_info is None:
            return

        self.content_info = build_early_content_info(
            self.playlist_info,
            self.url,
            self.audio_format,
        )

        self._emit(
            ProgressStep.FETCHING_INFO,
            f"Found: {self.content_info.title}",
            1.0,  # Small progress to show activity
            {"content_info": self.content_info.model_dump()},
        )

    def _update_content_info_complete(self) -> None:
        """Update content_info with complete track data."""
        if self.playlist_info is None or not self.tracks:
            return

        first_track = self.tracks[0]

        if self.content_info is None:
            # Fallback: build from scratch if early emission didn't happen
            self.content_info = build_content_info(
                self.playlist_info, self.tracks, self.url, self.audio_format
            )
        else:
            # Update existing content_info with track-derived data
            self.content_info.track_count = len(self.tracks)
            self.content_info.artist = _determine_artist(
                self.playlist_info, first_track
            )
            self.content_info.year = _extract_year(self.playlist_info, first_track)
            if not self.content_info.thumbnail_url and first_track.cover_url:
                self.content_info.thumbnail_url = first_track.cover_url

        track_word = "track" if len(self.tracks) == 1 else "tracks"
        message = f"Found {len(self.tracks)} {track_word}: {self.content_info.title}"

        self._emit(
            ProgressStep.FETCHING_INFO,
            message,
            PHASE_RANGES["extracting"].end,
            {"content_info": self.content_info.model_dump()},
        )

    def _handle_download(
        self,
        progress: PlaylistProgress,
        step: ProgressStep,
        percent: float,
    ) -> None:
        """Process download phase progress update."""
        self._emit(step, _format_download_message(progress), percent)

        # Update bitrate from first successful download
        self._update_bitrate_if_available(progress)

    def _update_bitrate_if_available(self, progress: PlaylistProgress) -> None:
        """Set audio_bitrate from first successful download result."""
        if not progress.download_progress:
            return
        if self.content_info is None or self.content_info.audio_bitrate is not None:
            return

        result = progress.download_progress.result
        if result.status == DownloadStatus.SUCCESS and result.bitrate:
            self.content_info.audio_bitrate = result.bitrate

    def _build_result(self, downloader: PlaylistDownloadService) -> SyncResult:
        """Construct final result from downloader state."""
        result = downloader.get_result()

        if result is None:
            return SyncResult(
                success=False,
                content_info=self.content_info,
                error="No tracks found",
            )

        destination = self._determine_destination(result)

        self._emit(ProgressStep.COMPLETED, f"Sync complete: {destination}", 100.0)

        return SyncResult(
            success=True,
            content_info=self.content_info,
            download_stats=result.download_stats,
            destination=destination,
        )

    def _determine_destination(self, result: Any) -> str | None:
        """Extract output directory from download results."""
        # Prefer M3U path's parent if generated
        if result.m3u_path:
            return str(result.m3u_path.parent)

        # Fall back to first download result's directory
        for dl_result in result.download_results:
            if dl_result.output_path:
                return str(dl_result.output_path.parent)

        return None

    def _emit(
        self,
        step: ProgressStep,
        message: str,
        percent: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Send progress update via callback if registered."""
        if self.on_progress:
            self.on_progress(step, message, percent, details)
