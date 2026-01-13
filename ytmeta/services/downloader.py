"""Download service for YouTube Music tracks using yt-dlp."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

import yt_dlp

from ytmeta.config import DownloadConfig
from ytmeta.exceptions import DownloadError
from ytmeta.models.domain import TrackMetadata
from ytmeta.utils.filename import build_track_path

logger = logging.getLogger(__name__)


class DownloadStatus(StrEnum):
    """Status of a download operation."""

    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class DownloadResult:
    """Result of a single track download.

    Attributes:
        track: The track metadata that was downloaded.
        status: The download status.
        output_path: Path to the downloaded file (if successful).
        error: Error message (if failed).
        video_id_used: The video ID that was used for download.
    """

    track: TrackMetadata
    status: DownloadStatus
    output_path: Path | None = None
    error: str | None = None
    video_id_used: str | None = None


class DownloaderProtocol(Protocol):
    """Protocol for download backends.

    This protocol enables dependency injection and testing.
    Implement this protocol to create mock downloaders for testing.
    """

    def download(self, video_id: str, output_path: Path) -> None:
        """Download a track to the specified path."""
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

    def _build_opts(self, output_path: Path) -> dict:
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

    def download(self, video_id: str, output_path: Path) -> None:
        """Download a track to the specified path.

        Args:
            video_id: YouTube video ID.
            output_path: Target path for the downloaded file (without extension).

        Raises:
            DownloadError: If download fails.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        opts = self._build_opts(output_path)
        url = self.YOUTUBE_MUSIC_URL.format(video_id=video_id)

        logger.debug("Downloading %s to %s", video_id, output_path)

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as e:
            logger.error("Failed to download %s: %s", video_id, e)
            raise DownloadError(f"Failed to download {video_id}: {e}") from e


class DownloadService:
    """Service for downloading YouTube Music tracks.

    This service orchestrates the download process:
    1. Build output path from track metadata using filename utilities
    2. Select video ID (prefer ATV if configured)
    3. Download using yt-dlp
    4. Report progress and results

    Example:
        >>> from ytmeta.config import DownloadConfig
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
        """
        if track.atv_video_id:
            return track.atv_video_id
        return track.omv_video_id

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
            artist=track.albumartist or track.artist,
            year=track.year,
            album=track.album,
            track_number=track.tracknumber,
            title=track.title,
        )

    def _get_expected_output_file(self, output_path: Path) -> Path | None:
        """Find the expected output file with extension.

        Args:
            output_path: Base output path without extension.

        Returns:
            Path to existing file if found, None otherwise.
        """
        # Check for file with the expected codec extension
        expected = output_path.with_suffix(f".{self._config.codec.value}")
        if expected.exists():
            return expected

        # Also check common alternatives (yt-dlp may choose different format)
        for ext in [".opus", ".mp3", ".m4a", ".flac", ".ogg", ".webm"]:
            alt_path = output_path.with_suffix(ext)
            if alt_path.exists():
                return alt_path

        return None

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
        video_id = self._get_video_id(track)

        # Always skip existing files
        existing = self._get_expected_output_file(output_path)
        if existing:
            logger.debug("Skipping existing file: %s", existing)
            return DownloadResult(
                track=track,
                status=DownloadStatus.SKIPPED,
                output_path=existing,
                video_id_used=video_id,
            )

        try:
            self._downloader.download(video_id, output_path)
            # Find the actual output file (yt-dlp adds extension)
            actual_path = self._get_expected_output_file(output_path) or output_path
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

    def download_tracks(
        self,
        tracks: list[TrackMetadata],
        on_progress: Callable[[int, int, DownloadResult], None] | None = None,
    ) -> list[DownloadResult]:
        """Download multiple tracks.

        Args:
            tracks: List of track metadata to download.
            on_progress: Optional callback for progress updates
                (current, total, result).

        Returns:
            List of DownloadResults.
        """
        results: list[DownloadResult] = []
        total = len(tracks)

        for i, track in enumerate(tracks):
            logger.info(
                "Downloading [%d/%d]: %s - %s",
                i + 1,
                total,
                track.artist,
                track.title,
            )

            result = self.download_track(track)
            results.append(result)

            if on_progress:
                on_progress(i + 1, total, result)

        # Log summary
        success = sum(1 for r in results if r.status == DownloadStatus.SUCCESS)
        skipped = sum(1 for r in results if r.status == DownloadStatus.SKIPPED)
        failed = sum(1 for r in results if r.status == DownloadStatus.FAILED)
        logger.info(
            "Download complete: %d success, %d skipped, %d failed",
            success,
            skipped,
            failed,
        )

        return results

    async def download_track_async(
        self,
        track: TrackMetadata,
    ) -> DownloadResult:
        """Async version of download_track().

        Runs the synchronous download in a thread pool to avoid blocking
        the event loop. Use this method in async contexts.

        Args:
            track: Track metadata.

        Returns:
            DownloadResult with status and path.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.download_track, track)

    async def download_tracks_async(
        self,
        tracks: list[TrackMetadata],
        on_progress: Callable[[int, int, DownloadResult], None] | None = None,
    ) -> list[DownloadResult]:
        """Async version of download_tracks().

        Runs the synchronous download_tracks() in a thread pool to avoid
        blocking the event loop. Use this method in async contexts.

        Args:
            tracks: List of track metadata to download.
            on_progress: Optional callback for progress updates
                (current, total, result).

        Returns:
            List of DownloadResults.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.download_tracks,
            tracks,
            on_progress,
        )
