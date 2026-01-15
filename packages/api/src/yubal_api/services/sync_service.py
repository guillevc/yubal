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
    PlaylistDownloadConfig,
    PlaylistProgress,
    TrackMetadata,
    create_playlist_downloader,
)
from yubal.models.domain import PlaylistInfo

from yubal_api.core.enums import ProgressStep
from yubal_api.core.models import AlbumInfo
from yubal_api.services.sync.cancel import CancelToken

logger = logging.getLogger(__name__)

# Phase mapping from yubal to API (fail-fast)
_PHASE_MAP = {
    "extracting": ProgressStep.FETCHING_INFO,
    "downloading": ProgressStep.DOWNLOADING,
    "composing": ProgressStep.IMPORTING,
}


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    album_info: AlbumInfo | None = None
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
    year_int: int | None = None
    if first and first.year:
        try:
            year_int = int(first.year)
        except ValueError:
            year_int = None

    return AlbumInfo(
        title=playlist_info.title or "Unknown",
        artist=first.primary_album_artist if first else "Various Artists",
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
            max_items: Maximum number of tracks to download (playlists only).

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

            # Iterate through all phases
            for progress in service.download_playlist(url, cancel_token):
                step = _map_phase(progress.phase)

                if progress.phase == "extracting":
                    # Collect tracks for album_info building
                    if progress.extract_progress:
                        tracks.append(progress.extract_progress.track)
                        playlist_info = progress.extract_progress.playlist_info

                    # Scale to 0-10%
                    pct = (
                        (progress.current / progress.total) * 10.0
                        if progress.total
                        else 0.0
                    )
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
                            10.0,
                            {"album_info": album_info.model_dump()},
                        )

                elif progress.phase == "downloading":
                    # Scale to 10-90%
                    pct = (
                        10.0 + (progress.current / progress.total) * 80.0
                        if progress.total
                        else 10.0
                    )
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
                    # Scale to 90-100%
                    pct = (
                        90.0 + (progress.current / progress.total) * 10.0
                        if progress.total
                        else 90.0
                    )
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
                destination=destination,
            )

        except CancellationError:
            return SyncResult(
                success=False,
                album_info=album_info,
                error="Cancelled",
            )
        except Exception as e:
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
            status_msg = (
                "downloaded"
                if result.status == DownloadStatus.SUCCESS
                else result.status.value
            )
            return f"[{dp.current}/{dp.total}] {result.track.title}: {status_msg}"
        return f"Downloading {progress.current}/{progress.total}..."
