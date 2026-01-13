"""Unified sync service using yubal library."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yubal import (
    AudioCodec,
    DownloadConfig,
    DownloadResult,
    DownloadStatus,
    TrackMetadata,
    create_downloader,
    create_extractor,
)
from yubal.models.domain import PlaylistInfo
from yubal.utils import is_album_playlist, write_m3u

from yubal_api.core.enums import ProgressStep
from yubal_api.core.models import AlbumInfo
from yubal_api.services.sync.cancel import CancelToken


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    album_info: AlbumInfo | None = None
    destination: str | None = None
    error: str | None = None


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
        thumbnail_url=first.cover_url if first else None,
        audio_codec=audio_format.upper(),
        audio_bitrate=None,  # Set after download
    )


class SyncService:
    """Unified sync service wrapping yubal library.

    Orchestrates extraction, download, and M3U generation.
    Provides progress callbacks compatible with the job system.
    """

    def __init__(self, base_path: Path, audio_format: str = "opus") -> None:
        """Initialize the sync service.

        Args:
            base_path: Base directory for downloads.
            audio_format: Audio format (opus, mp3, m4a).
        """
        self._base_path = base_path
        self._audio_format = audio_format
        self._codec = AudioCodec(audio_format)

    def execute(
        self,
        url: str,
        progress_callback: (
            Callable[[ProgressStep, str, float | None, dict[str, Any] | None], None]
            | None
        ),
        cancel_token: CancelToken,
    ) -> SyncResult:
        """Execute extraction + download workflow.

        Progress phases:
        - 0-10%: Extracting metadata
        - 10-90%: Downloading tracks
        - 90-100%: Finalization (M3U for playlists)

        Args:
            url: YouTube Music album/playlist URL.
            progress_callback: Optional callback for progress updates.
            cancel_token: Token for cancellation.

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
            # Phase 1: Extract metadata (0% -> 10%)
            emit(ProgressStep.FETCHING_INFO, "Extracting metadata...", 0.0)

            extractor = create_extractor()

            for progress in extractor.extract(url):
                if cancel_token.is_cancelled():
                    return SyncResult(success=False, error="Cancelled")

                tracks.append(progress.track)
                playlist_info = progress.playlist_info

                # Scale to 0-10%
                pct = (progress.current / progress.total) * 10.0
                cur, tot = progress.current, progress.total
                msg = f"Extracted {cur}/{tot}: {progress.track.title}"
                emit(ProgressStep.FETCHING_INFO, msg, pct)

            if not tracks or not playlist_info:
                return SyncResult(success=False, error="No tracks found")

            # Build album_info for frontend
            album_info = album_info_from_yubal(
                playlist_info, tracks, url, self._audio_format
            )
            emit(
                ProgressStep.FETCHING_INFO,
                f"Found {len(tracks)} tracks: {album_info.title}",
                10.0,
                {"album_info": album_info.model_dump()},
            )

            if cancel_token.is_cancelled():
                return SyncResult(
                    success=False, album_info=album_info, error="Cancelled"
                )

            # Phase 2: Download tracks (10% -> 90%)
            emit(ProgressStep.DOWNLOADING, "Starting download...", 10.0)

            config = DownloadConfig(
                base_path=self._base_path,
                codec=self._codec,
                quiet=True,
            )
            downloader = create_downloader(config)

            downloaded: list[DownloadResult] = []
            failed_count = 0

            for progress in downloader.download_tracks(tracks):
                if cancel_token.is_cancelled():
                    return SyncResult(
                        success=False, album_info=album_info, error="Cancelled"
                    )

                result = progress.result
                if result.status == DownloadStatus.SUCCESS and result.output_path:
                    downloaded.append(result)
                elif result.status == DownloadStatus.SKIPPED and result.output_path:
                    downloaded.append(result)
                else:
                    failed_count += 1

                # Scale to 10-90%
                pct = 10.0 + (progress.current / progress.total) * 80.0
                status_msg = (
                    "downloaded"
                    if result.status == DownloadStatus.SUCCESS
                    else result.status.value
                )
                cur, tot = progress.current, progress.total
                msg = f"[{cur}/{tot}] {result.track.title}: {status_msg}"
                emit(ProgressStep.DOWNLOADING, msg, pct)

            if not downloaded:
                return SyncResult(
                    success=False,
                    album_info=album_info,
                    error="All downloads failed",
                )

            # Update bitrate from first downloaded file
            bitrate = downloaded[0].bitrate
            if bitrate:
                album_info.audio_bitrate = bitrate

            # Phase 3: Finalization (90% -> 100%)
            emit(ProgressStep.IMPORTING, "Finalizing...", 90.0)

            # Determine destination from first downloaded file
            destination = str(downloaded[0].output_path.parent)

            # Generate M3U for playlists (not albums)
            if playlist_info.title and not is_album_playlist(playlist_info.playlist_id):
                emit(ProgressStep.IMPORTING, "Generating playlist file...", 95.0)
                tracks_for_m3u = [(r.track, r.output_path) for r in downloaded]
                m3u_path = write_m3u(
                    self._base_path, playlist_info.title, tracks_for_m3u
                )
                destination = str(m3u_path.parent)

            emit(ProgressStep.COMPLETED, f"Sync complete: {destination}", 100.0)

            return SyncResult(
                success=True,
                album_info=album_info,
                destination=destination,
            )

        except Exception as e:
            emit(ProgressStep.FAILED, str(e))
            return SyncResult(
                success=False,
                album_info=album_info,
                error=str(e),
            )
