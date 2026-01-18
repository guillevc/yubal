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


# ============================================================================
# PROTOCOL & CONSTANTS
# ============================================================================


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


# ============================================================================
# YT-DLP BACKEND - Low-level downloader using yt-dlp library
# ============================================================================


class YTDLPDownloader:
    """yt-dlp based downloader for YouTube Music tracks.

    Wraps yt-dlp with consistent configuration and error handling.
    Implements DownloaderProtocol for dependency injection and testing.

    The downloader handles:
    - Audio extraction with FFmpeg post-processing
    - Output path management (creates directories as needed)
    - Capture of actual output path (which may differ from template)
    """

    YOUTUBE_MUSIC_URL = "https://music.youtube.com/watch?v={video_id}"

    def __init__(self, config: DownloadConfig) -> None:
        """Initialize the downloader.

        Args:
            config: Download configuration (codec, quality, output paths).
        """
        self._config = config

    def _build_yt_dlp_options(self, output_path: Path) -> dict[str, Any]:
        """Build yt-dlp options for audio extraction and post-processing.

        Why these options: Configures yt-dlp to download best audio quality and
        convert to the target codec (e.g., MP3, M4A) using FFmpeg. The quiet
        flags control console output verbosity.

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
        """Download a track and extract audio to the specified path.

        Why hook-based path capture: yt-dlp may change the output filename during
        post-processing (e.g., adding codec extension). We use a postprocessor hook
        to capture the actual output path after FFmpeg completes.

        Error handling: Provides specific error messages for common issues like
        region-locked videos or authentication requirements, making debugging easier.

        Args:
            video_id: YouTube video ID.
            output_path: Target path for the downloaded file (without extension).

        Returns:
            Actual path where file was saved (with extension).

        Raises:
            DownloadError: If download fails.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        opts = self._build_yt_dlp_options(output_path)
        url = self.YOUTUBE_MUSIC_URL.format(video_id=video_id)

        logger.debug("Downloading %s to %s", video_id, output_path)

        actual_path: Path | None = None

        def capture_postprocessed_path(d: dict[str, Any]) -> None:
            """Capture the final output path after FFmpeg post-processing."""
            nonlocal actual_path
            # Capture filepath after FFmpeg postprocessor completes
            if d["status"] == "finished":
                filepath = d.get("info_dict", {}).get("filepath")
                if filepath:
                    actual_path = Path(filepath)

        opts["postprocessor_hooks"] = [capture_postprocessed_path]

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            error_msg = str(e)
            # Provide more helpful error messages for common issues
            if "Video unavailable" in error_msg:
                logger.error("Video %s is unavailable (may be region-locked)", video_id)
                raise DownloadError(
                    f"Video {video_id} is unavailable (may be region-locked or removed)"
                ) from e
            if "Sign in" in error_msg or "cookies" in error_msg.lower():
                logger.error("Authentication required for video %s", video_id)
                raise DownloadError(
                    f"Authentication required for {video_id}. "
                    "Try providing a cookies.txt file."
                ) from e
            logger.error("Failed to download %s: %s", video_id, e)
            raise DownloadError(f"Failed to download {video_id}: {e}") from e

        # Return actual path captured by hook, or fallback to expected path
        return self._resolve_output_path(actual_path, output_path)

    def _resolve_output_path(
        self, captured_path: Path | None, expected_path: Path
    ) -> Path:
        """Resolve the final output path after download.

        Why fallback logic: If the hook didn't capture the path (edge cases,
        yt-dlp internals changed), we construct the expected path by adding
        the codec extension.

        Args:
            captured_path: Path captured by postprocessor hook (may be None).
            expected_path: Expected output path without extension.

        Returns:
            Final output path with extension.
        """
        # Use captured path if available and exists
        if captured_path and captured_path.exists():
            return captured_path

        # Fallback to expected path with codec extension
        # (use string concat - with_suffix breaks on dots in filename)
        expected_with_ext = Path(f"{expected_path}.{self._config.codec.value}")
        if expected_with_ext.exists():
            return expected_with_ext

        return expected_path


# ============================================================================
# DOWNLOAD SERVICE - High-level orchestration for track downloads
# ============================================================================


class DownloadService:
    """Service for downloading YouTube Music tracks.

    Pipeline Overview:
    ==================
    1. download_tracks() - Main entry point: iterates through tracks,
                          yields progress updates as downloads complete
    2. download_track() - Downloads single track: checks if exists,
                         selects video ID, downloads, tags with metadata
    3. _select_video_id_for_download() - Chooses ATV or OMV video ID
                         based on availability (prefers ATV for audio quality)
    4. _build_output_path_for_track() - Constructs file path using artist,
                         album, and track metadata
    5. _apply_metadata_tags() - Tags downloaded file with ID3/MP4 tags
                         and embeds cover art

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

    # ============================================================================
    # PUBLIC API - Main entry points for downloading tracks
    # ============================================================================

    def download_tracks(
        self,
        tracks: list[TrackMetadata],
        cancel_token: CancelToken | None = None,
    ) -> Iterator[DownloadProgress]:
        """Download multiple tracks with progress updates.

        Yields progress updates as each track is downloaded, making this ideal
        for CLI progress bars or UI updates. Supports cancellation via token.

        Why yield progress: Allows callers to display real-time feedback during
        long-running downloads (some playlists have hundreds of tracks).

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

    def download_track(
        self,
        track: TrackMetadata,
    ) -> DownloadResult:
        """Download a single track with metadata tagging.

        Download pipeline:
        1. Build output path from track metadata
        2. Skip if file already exists (no overwrite)
        3. Select video ID (prefer ATV for audio quality)
        4. Download audio using yt-dlp
        5. Apply metadata tags (ID3/MP4) and embed cover art

        Why skip existing: Prevents re-downloading tracks if the download is
        interrupted and resumed. Users can manually delete files to re-download.

        Args:
            track: Track metadata.

        Returns:
            DownloadResult with status, path, and any error information.
        """
        output_path = self._build_output_path_for_track(track)

        try:
            video_id = self._select_video_id_for_download(track)
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

            # Tag the downloaded file with metadata
            self._apply_metadata_tags(actual_path, track)

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

    # ============================================================================
    # VIDEO ID SELECTION - Choose best video variant for download
    # ============================================================================

    def _select_video_id_for_download(self, track: TrackMetadata) -> str:
        """Select the best video ID for downloading the track.

        Video ID Selection Priority:
        1. ATV (Audio Track Video) - Album version, best audio quality
        2. OMV (Official Music Video) - Fallback, may have different audio mix

        Why prefer ATV: Audio Track Videos contain the canonical album version
        with best audio quality. OMVs may have different mixing, radio edits,
        or background noise from the video.

        Args:
            track: Track metadata containing video IDs.

        Returns:
            Video ID to download.

        Raises:
            DownloadError: If no video ID is available for the track.
        """
        video_id = track.atv_video_id or track.omv_video_id
        if not video_id:
            raise DownloadError(
                f"No video ID available for track: '{track.title}' by {track.artist}"
            )
        return video_id

    # ============================================================================
    # PATH CONSTRUCTION - Build output paths from track metadata
    # ============================================================================

    def _build_output_path_for_track(self, track: TrackMetadata) -> Path:
        """Build output path for a track using organized directory structure.

        Creates a hierarchical path structure that organizes tracks by artist
        and album, making it easy to browse the music library in a file manager.

        Path structure: base_path/Artist/YEAR - Album/NN - Title
        Example: Music/Pink Floyd/1973 - The Dark Side of the Moon/01 - Speak to Me

        Why this structure: Standard music library organization that's intuitive
        for users and compatible with most music players. The extension is added
        by yt-dlp during post-processing.

        Args:
            track: Track metadata.

        Returns:
            Output path (without extension, yt-dlp adds it during download).
        """
        return build_track_path(
            base=self._config.base_path,
            artist=track.primary_album_artist,
            year=track.year,
            album=track.album,
            track_number=track.track_number,
            title=track.title,
        )

    # ============================================================================
    # METADATA TAGGING - Embed ID3/MP4 tags and cover art
    # ============================================================================

    def _apply_metadata_tags(self, path: Path, track: TrackMetadata) -> None:
        """Apply ID3/MP4 metadata tags and embed cover art to audio file.

        Downloads the cover art from YouTube and embeds it along with all track
        metadata (title, artist, album, track number, year, etc.) into the audio
        file using the appropriate tagging format (ID3 for MP3, MP4 tags for M4A).

        Why non-fatal: Tagging failures shouldn't delete the successfully downloaded
        audio file. Users can manually tag files later if needed. Common failures
        include network issues fetching cover art or unsupported codec formats.

        Args:
            path: Path to the audio file.
            track: Track metadata.
        """
        try:
            cover = fetch_cover(track.cover_url)
            tag_track(path, track, cover)
        except Exception as e:
            logger.warning("Failed to tag %s: %s", path, e)
