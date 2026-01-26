"""Unified sync service using yubal library."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yubal import (
    AudioCodec,
    CancellationError,
    DownloadConfig,
    DownloadStatus,
    PhaseStats,
    PlaylistDownloadConfig,
    PlaylistProgress,
    TrackMetadata,
    URLType,
    create_playlist_downloader,
    detect_url_type,
)
from yubal.models.domain import ContentKind, PlaylistInfo

from yubal_api.core.enums import ProgressStep
from yubal_api.core.models import AlbumInfo
from yubal_api.services.sync.cancel import CancelToken

logger = logging.getLogger(__name__)

# Progress percentage boundaries for each phase
# Extraction: 0-10%, Download: 10-90%, Compose: 90-100%
_PROGRESS_PHASES = {
    "extracting": (0.0, 10.0),  # 0% to 10%
    "downloading": (10.0, 90.0),  # 10% to 90%
    "composing": (90.0, 100.0),  # 90% to 100%
}

# Phase mapping from yubal to API (fail-fast on unknown phases)
_PHASE_MAP = {
    "extracting": ProgressStep.FETCHING_INFO,
    "downloading": ProgressStep.DOWNLOADING,
    "composing": ProgressStep.IMPORTING,
}


def _calculate_phase_progress(phase: str, current: int, total: int) -> float:
    """Calculate overall progress percentage for a phase.

    Maps the current/total progress within a phase to the overall 0-100% scale.

    Args:
        phase: Current phase name (extracting, downloading, composing).
        current: Current item number in the phase.
        total: Total items in the phase.

    Returns:
        Progress percentage in the 0-100 range.
    """
    if total == 0:
        return _PROGRESS_PHASES.get(phase, (0.0, 0.0))[0]

    start, end = _PROGRESS_PHASES.get(phase, (0.0, 0.0))
    phase_range = end - start
    return start + (current / total) * phase_range


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    album_info: AlbumInfo | None = None
    download_stats: PhaseStats | None = None
    destination: str | None = None
    error: str | None = None


def _map_phase(phase: str) -> ProgressStep:
    """Map yubal phase to API ProgressStep (fail-fast)."""
    if phase not in _PHASE_MAP:
        raise ValueError(f"Unknown phase: {phase}")
    return _PHASE_MAP[phase]


def album_info_from_yubal(
    playlist_info: PlaylistInfo,
    tracks: list[TrackMetadata],
    url: str,
    audio_format: str,
) -> AlbumInfo:
    """Map yubal's extraction result to API's AlbumInfo schema."""
    first = tracks[0] if tracks else None

    # Only include year for albums, not playlists
    year_int: int | None = None
    if playlist_info.kind != ContentKind.PLAYLIST and first and first.year:
        try:
            year_int = int(first.year)
        except ValueError:
            year_int = None

    # Use channel name for playlists, album artist for albums
    if playlist_info.kind == ContentKind.PLAYLIST and playlist_info.author:
        artist = playlist_info.author
    else:
        artist = first.primary_album_artist if first else "Various Artists"

    return AlbumInfo(
        title=playlist_info.title or "Unknown",
        artist=artist,
        year=year_int,
        track_count=len(tracks),
        playlist_id=playlist_info.playlist_id,
        url=url,
        thumbnail_url=playlist_info.cover_url or (first.cover_url if first else None),
        audio_codec=audio_format.upper(),
        audio_bitrate=None,  # Set after download
        kind=playlist_info.kind.value,
    )


class SyncService:
    """Unified sync service wrapping yubal library.

    Thin adapter over yubal's PlaylistDownloadService.
    Provides progress callbacks compatible with the job system.
    """

    def __init__(
        self,
        base_path: Path,
        audio_format: str = "opus",
        cookies_path: Path | None = None,
    ) -> None:
        """Initialize the sync service.

        Args:
            base_path: Base directory for downloads.
            audio_format: Audio format (opus, mp3, m4a).
            cookies_path: Optional path to cookies.txt for YouTube Music auth.
        """
        self._base_path = base_path
        self._audio_format = audio_format
        self._codec = AudioCodec(audio_format)
        self._cookies_path = cookies_path

    def execute(
        self,
        url: str,
        progress_callback: (
            Callable[[ProgressStep, str, float | None, dict[str, Any] | None], None]
            | None
        ),
        cancel_token: CancelToken,
        max_items: int | None = None,
    ) -> SyncResult:
        """Execute extraction + download workflow.

        Progress phases:
        - 0-10%: Extracting metadata
        - 10-90%: Downloading tracks
        - 90-100%: Finalization (M3U and cover)

        Args:
            url: YouTube Music album/playlist URL.
            progress_callback: Optional callback for progress updates.
            cancel_token: Token for cancellation.
            max_items: Maximum number of tracks to download.

        Returns:
            SyncResult with success status and details.
        """

        def emit(
            step: ProgressStep,
            msg: str,
            pct: float | None = None,
            details: dict[str, Any] | None = None,
        ) -> None:
            if progress_callback:
                progress_callback(step, msg, pct, details)

        album_info: AlbumInfo | None = None
        tracks: list[TrackMetadata] = []
        playlist_info: PlaylistInfo | None = None

        try:
            # Create playlist download service
            config = PlaylistDownloadConfig(
                download=DownloadConfig(
                    base_path=self._base_path,
                    codec=self._codec,
                    quiet=True,
                ),
                generate_m3u=True,
                save_cover=True,
                max_items=max_items,
            )
            service = create_playlist_downloader(
                config, cookies_path=self._cookies_path
            )

            emit(ProgressStep.FETCHING_INFO, "Starting...", 0.0)

            # Check if this is a single song URL
            url_type = detect_url_type(url)
            if url_type == URLType.SONG:
                return self._execute_song_download(
                    service, url, cancel_token, emit
                )

            # Iterate through all phases for playlist/album
            for progress in service.download_playlist(url, cancel_token):
                step = _map_phase(progress.phase)

                # Calculate progress percentage using the helper
                pct = _calculate_phase_progress(
                    progress.phase, progress.current, progress.total
                )

                if progress.phase == "extracting":
                    # Collect tracks for album_info building
                    if progress.extract_progress:
                        tracks.append(progress.extract_progress.track)
                        playlist_info = progress.extract_progress.playlist_info

                    msg = self._format_extract_message(progress)
                    emit(step, msg, pct)

                    # Build album_info when extraction completes
                    if progress.current == progress.total and playlist_info and tracks:
                        album_info = album_info_from_yubal(
                            playlist_info, tracks, url, self._audio_format
                        )
                        emit(
                            step,
                            f"Found {len(tracks)} tracks: {album_info.title}",
                            pct,
                            {"album_info": album_info.model_dump()},
                        )

                elif progress.phase == "downloading":
                    msg = self._format_download_message(progress)
                    emit(step, msg, pct)

                    # Update bitrate from first successful download
                    if (
                        progress.download_progress
                        and album_info
                        and not album_info.audio_bitrate
                    ):
                        result = progress.download_progress.result
                        if result.status == DownloadStatus.SUCCESS and result.bitrate:
                            album_info.audio_bitrate = result.bitrate

                elif progress.phase == "composing":
                    msg = progress.message or "Generating playlist files..."
                    emit(step, msg, pct)

            # Get final result
            result = service.get_result()
            if not result:
                return SyncResult(
                    success=False, album_info=album_info, error="No tracks found"
                )

            # Determine destination from results
            destination: str | None = None
            for dl_result in result.download_results:
                if dl_result.output_path:
                    destination = str(dl_result.output_path.parent)
                    break

            # Use M3U path's parent if we generated a playlist
            if result.m3u_path:
                destination = str(result.m3u_path.parent)

            emit(ProgressStep.COMPLETED, f"Sync complete: {destination}", 100.0)

            return SyncResult(
                success=True,
                album_info=album_info,
                download_stats=result.download_stats,
                destination=destination,
            )

        except CancellationError:
            logger.info("Download cancelled", extra={"status": "failed"})
            return SyncResult(
                success=False,
                album_info=album_info,
                error="Cancelled",
            )
        except Exception as e:
            logger.exception("Sync failed: %s", e)
            emit(ProgressStep.FAILED, str(e))
            return SyncResult(
                success=False,
                album_info=album_info,
                error=str(e),
            )

    def _format_extract_message(self, progress: PlaylistProgress) -> str:
        """Format progress message for extraction phase."""
        if progress.extract_progress:
            ep = progress.extract_progress
            return f"Extracted {ep.current}/{ep.total}: {ep.track.title}"
        return f"Extracting {progress.current}/{progress.total}..."

    def _format_download_message(self, progress: PlaylistProgress) -> str:
        """Format progress message for download phase."""
        if progress.download_progress:
            dp = progress.download_progress
            result = dp.result
            if result.status == DownloadStatus.SUCCESS:
                status_msg = "downloaded"
            elif result.status == DownloadStatus.SKIPPED and result.skip_reason:
                # Show human-readable skip reason
                reason_display = result.skip_reason.value.replace("_", " ")
                status_msg = f"skipped ({reason_display})"
            else:
                status_msg = result.status.value
            return f"[{dp.current}/{dp.total}] {result.track.title}: {status_msg}"
        return f"Downloading {progress.current}/{progress.total}..."

    def _execute_song_download(
        self,
        service: Any,
        url: str,
        cancel_token: CancelToken,
        emit: Callable[[ProgressStep, str, float | None, dict[str, Any] | None], None],
    ) -> SyncResult:
        """Execute download for a single song URL.

        Simplified pipeline without M3U generation.

        Args:
            service: The playlist download service instance.
            url: YouTube Music watch URL.
            cancel_token: Token for cancellation.
            emit: Progress callback function.

        Returns:
            SyncResult with success status and details.
        """
        emit(ProgressStep.FETCHING_INFO, "Fetching song info...", 5.0)

        # Download the song
        song_result = service.download_song(url, cancel_token)
        track = song_result.track
        dl_result = song_result.download_result

        # Build album info for UI display
        album_info = AlbumInfo(
            title=track.album or track.title,
            artist=track.artist,
            year=int(track.year) if track.year else None,
            track_count=1,
            playlist_id=dl_result.video_id_used or "",
            url=url,
            thumbnail_url=track.cover_url,
            audio_codec=self._audio_format.upper(),
            audio_bitrate=dl_result.bitrate,
            kind=ContentKind.SONG.value,
        )

        emit(
            ProgressStep.FETCHING_INFO,
            f"Found: {track.title} by {track.artist}",
            10.0,
            {"album_info": album_info.model_dump()},
        )

        # Report download result
        if dl_result.status == DownloadStatus.SUCCESS:
            emit(ProgressStep.DOWNLOADING, f"Downloaded: {track.title}", 90.0)
            destination = str(dl_result.output_path.parent) if dl_result.output_path else None
            emit(ProgressStep.COMPLETED, f"Song download complete: {destination}", 100.0)
            return SyncResult(
                success=True,
                album_info=album_info,
                download_stats=PhaseStats(success=1),
                destination=destination,
            )
        elif dl_result.status == DownloadStatus.SKIPPED:
            reason = dl_result.skip_reason.value if dl_result.skip_reason else "unknown"
            emit(ProgressStep.DOWNLOADING, f"Skipped: {track.title} ({reason})", 90.0)
            destination = str(dl_result.output_path.parent) if dl_result.output_path else None
            emit(ProgressStep.COMPLETED, "Song already exists", 100.0)
            return SyncResult(
                success=True,
                album_info=album_info,
                download_stats=PhaseStats(skipped_by_reason={dl_result.skip_reason: 1} if dl_result.skip_reason else {}),
                destination=destination,
            )
        else:
            error_msg = dl_result.error or "Download failed"
            emit(ProgressStep.FAILED, error_msg)
            return SyncResult(
                success=False,
                album_info=album_info,
                download_stats=PhaseStats(failed=1),
                error=error_msg,
            )
