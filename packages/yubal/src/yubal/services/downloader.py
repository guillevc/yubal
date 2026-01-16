"""Download service for YouTube Music tracks using yt-dlp."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Protocol

import yt_dlp

from yubal.config import DownloadConfig
from yubal.exceptions import CancellationError, DownloadError
from yubal.models.domain import (
    CancelToken,
    DownloadProgress,
    DownloadResult,
    DownloadStatus,
    TrackMetadata,
)
from yubal.services.tagger import tag_track
from yubal.utils.cover import fetch_cover
from yubal.utils.filename import build_track_path

logger = logging.getLogger(__name__)


class DownloaderProtocol(Protocol):
    """Protocol for download backends.

    This protocol enables dependency injection and testing.
    Implement this protocol to create mock downloaders for testing.
    """

    def download(self, video_id: str, output_path: Path) -> Path:
        """Download a track to the specified path.

        Returns:
            Actual path where file was saved (with extension).
        """
        ...


class YTDLPDownloader:
    """yt-dlp based downloader.

    Wraps yt-dlp with consistent configuration and error handling.
    Implements DownloaderProtocol for type safety.
    """

    YOUTUBE_MUSIC_URL = "https://music.youtube.com/watch?v={video_id}"

    def __init__(self, config: DownloadConfig) -> None:
        """Initialize the downloader.

        Args:
            config: Download configuration.
        """
        self._config = config

    def _build_opts(self, output_path: Path) -> dict[str, Any]:
        """Build yt-dlp options for a download.

        Args:
            output_path: Target path for the downloaded file.

        Returns:
            Dictionary of yt-dlp options.
        """
        return {
            "format": "bestaudio/best",
            "outtmpl": str(output_path),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self._config.codec.value,
                    "preferredquality": str(self._config.quality),
                }
            ],
            "quiet": self._config.quiet,
            "no_warnings": self._config.quiet,
            "noprogress": self._config.quiet,
        }

    def download(self, video_id: str, output_path: Path) -> Path:
        """Download a track to the specified path.

        Args:
            video_id: YouTube video ID.
            output_path: Target path for the downloaded file (without extension).

        Returns:
            Actual path where file was saved (with extension).

        Raises:
            DownloadError: If download fails.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        opts = self._build_opts(output_path)
        url = self.YOUTUBE_MUSIC_URL.format(video_id=video_id)

        logger.debug("Downloading %s to %s", video_id, output_path)

        actual_path: Path | None = None

        def postprocessor_hook(d: dict[str, Any]) -> None:
            nonlocal actual_path
            # Capture filepath after FFmpeg postprocessor completes
            if d["status"] == "finished":
                filepath = d.get("info_dict", {}).get("filepath")
                if filepath:
                    actual_path = Path(filepath)

        opts["postprocessor_hooks"] = [postprocessor_hook]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            logger.error("Failed to download %s: %s", video_id, e)
            raise DownloadError(f"Failed to download {video_id}: {e}") from e

        # Return actual path, fallback to expected if hook didn't capture it
        if actual_path and actual_path.exists():
            return actual_path

        # Fallback to expected path with codec extension
        # (use string concat - with_suffix breaks on dots in filename)
        expected = Path(f"{output_path}.{self._config.codec.value}")
        if expected.exists():
            return expected

        return output_path


class DownloadService:
    """Service for downloading YouTube Music tracks.

    This service orchestrates the download process:
    1. Build output path from track metadata using filename utilities
    2. Select video ID (prefer ATV if configured)
    3. Download using yt-dlp
    4. Report progress and results

    Example:
        >>> from yubal.config import DownloadConfig
        >>> config = DownloadConfig(base_path=Path("./music"))
        >>> service = DownloadService(config)
        >>> result = service.download_track(track_metadata)
        >>> if result.status == DownloadStatus.SUCCESS:
        ...     print(f"Downloaded to: {result.output_path}")
    """

    def __init__(
        self,
        config: DownloadConfig,
        downloader: DownloaderProtocol | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            config: Download configuration.
            downloader: Optional downloader implementation.
                        Uses YTDLPDownloader if not provided.
        """
        self._config = config
        self._downloader = downloader or YTDLPDownloader(config)

    def _get_video_id(self, track: TrackMetadata) -> str:
        """Get the video ID to download.

        Always prefers ATV (Audio Track Video) for better audio quality,
        falling back to OMV (Official Music Video) if ATV is unavailable.

        Args:
            track: Track metadata.

        Returns:
            Video ID to download.

        Raises:
            DownloadError: If no video ID is available.
        """
        video_id = track.atv_video_id or track.omv_video_id
        if not video_id:
            raise DownloadError(f"No video ID available for track: {track.title}")
        return video_id

    def _build_output_path(self, track: TrackMetadata) -> Path:
        """Build output path for a track.

        Uses the filename utilities to create a path structure:
        base_path/Artist/YEAR - Album/NN - Title

        Args:
            track: Track metadata.

        Returns:
            Output path (without extension, yt-dlp adds it).
        """
        return build_track_path(
            base=self._config.base_path,
            artist=track.primary_album_artist,
            year=track.year,
            album=track.album,
            track_number=track.track_number,
            title=track.title,
        )

    def download_track(
        self,
        track: TrackMetadata,
    ) -> DownloadResult:
        """Download a single track.

        Always skips existing files (uses yt-dlp default behavior).

        Args:
            track: Track metadata.

        Returns:
            DownloadResult with status, path, and any error information.
        """
        output_path = self._build_output_path(track)

        try:
            video_id = self._get_video_id(track)
        except DownloadError as e:
            return DownloadResult(
                track=track,
                status=DownloadStatus.FAILED,
                error=str(e),
            )

        # Skip existing files (with_suffix breaks on dots in filename)
        expected = Path(f"{output_path}.{self._config.codec.value}")
        if expected.exists():
            logger.debug("Skipping existing file: %s", expected)
            return DownloadResult(
                track=track,
                status=DownloadStatus.SKIPPED,
                output_path=expected,
                video_id_used=video_id,
            )

        try:
            actual_path = self._downloader.download(video_id, output_path)

            # Tag the downloaded file
            self._tag_file(actual_path, track)

            logger.info(
                "Downloaded: '%s'",
                actual_path,
                extra={"status": "success", "file_path": str(actual_path)},
            )

            return DownloadResult(
                track=track,
                status=DownloadStatus.SUCCESS,
                output_path=actual_path,
                video_id_used=video_id,
            )
        except DownloadError as e:
            return DownloadResult(
                track=track,
                status=DownloadStatus.FAILED,
                error=str(e),
                video_id_used=video_id,
            )

    def _tag_file(self, path: Path, track: TrackMetadata) -> None:
        """Tag an audio file with track metadata.

        Fetches cover art and applies all metadata tags.
        Errors are logged but don't fail the download.

        Args:
            path: Path to the audio file.
            track: Track metadata.
        """
        try:
            cover = fetch_cover(track.cover_url)
            tag_track(path, track, cover)
        except Exception as e:
            logger.warning("Failed to tag %s: %s", path, e)

    def download_tracks(
        self,
        tracks: list[TrackMetadata],
        cancel_token: CancelToken | None = None,
    ) -> Iterator[DownloadProgress]:
        """Download multiple tracks.

        Yields progress updates as each track is downloaded.

        Args:
            tracks: List of track metadata to download.
            cancel_token: Optional token for cancellation support.

        Yields:
            DownloadProgress with current/total counts and the download result.

        Raises:
            CancellationError: If cancel_token.is_cancelled becomes True.

        Example:
            >>> for progress in downloader.download_tracks(tracks):
            ...     print(f"[{progress.current}/{progress.total}]")
        """
        total = len(tracks)

        for i, track in enumerate(tracks):
            # Check for cancellation before each download
            if cancel_token and cancel_token.is_cancelled:
                raise CancellationError("Download cancelled")

            logger.info(
                "%s - %s",
                track.artist,
                track.title,
                extra={
                    "event_type": "track_download",
                    "current": i + 1,
                    "total": total,
                    "track_title": track.title,
                    "track_artist": track.artist,
                },
            )

            result = self.download_track(track)
            yield DownloadProgress(current=i + 1, total=total, result=result)
