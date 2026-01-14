"""High-level playlist download service."""

import logging
from collections.abc import Iterator
from pathlib import Path

from yubal.client import YTMusicClient, YTMusicProtocol
from yubal.config import PlaylistDownloadConfig
from yubal.models.domain import (
    DownloadResult,
    PlaylistDownloadResult,
    PlaylistInfo,
    PlaylistProgress,
    TrackMetadata,
)
from yubal.services.composer import PlaylistComposerService
from yubal.services.downloader import DownloadService
from yubal.services.extractor import MetadataExtractorService

logger = logging.getLogger(__name__)


class PlaylistDownloadService:
    """High-level service for downloading complete playlists.

    Orchestrates the full workflow:
    1. Extract metadata from playlist URL
    2. Download all tracks
    3. Generate M3U and cover files

    This is the recommended way to download playlists when you want
    the complete workflow handled for you.

    Example:
        >>> from yubal import create_playlist_downloader
        >>> from yubal.config import PlaylistDownloadConfig, DownloadConfig
        >>>
        >>> config = PlaylistDownloadConfig(
        ...     download=DownloadConfig(base_path=Path("./music"))
        ... )
        >>> service = create_playlist_downloader(config)
        >>>
        >>> # With progress updates
        >>> for progress in service.download_playlist(url):
        ...     print(f"[{progress.phase}] {progress.current}/{progress.total}")
        >>> result = service.get_result()
        >>> print(f"Downloaded: {result.success_count}")
        >>>
        >>> # Or all at once
        >>> result = service.download_playlist_all(url)
    """

    def __init__(
        self,
        config: PlaylistDownloadConfig,
        *,
        client: YTMusicProtocol | None = None,
        extractor: MetadataExtractorService | None = None,
        downloader: DownloadService | None = None,
        composer: PlaylistComposerService | None = None,
        cookies_path: Path | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            config: Playlist download configuration.
            client: Optional YTMusic client (creates default if not provided).
            extractor: Optional extractor (creates from client if not provided).
            downloader: Optional downloader (creates from config if not provided).
            composer: Optional composer (creates default if not provided).
            cookies_path: Optional path to cookies.txt for authentication.
        """
        self._config = config

        # Create client if needed
        if client is None:
            client = YTMusicClient(cookies_path=cookies_path)

        # Create services
        self._extractor = extractor or MetadataExtractorService(client)
        self._downloader = downloader or DownloadService(config.download)
        self._composer = composer or PlaylistComposerService()

        # Store last result for retrieval after iteration
        self._last_result: PlaylistDownloadResult | None = None

    def download_playlist(self, url: str) -> Iterator[PlaylistProgress]:
        """Download a complete playlist with artifacts.

        Yields progress updates through all phases:
        1. "extracting" - Metadata extraction from YouTube Music
        2. "downloading" - Track downloads via yt-dlp
        3. "composing" - M3U and cover file generation

        Args:
            url: YouTube Music playlist URL.

        Yields:
            PlaylistProgress with phase and progress information.

        Example:
            >>> for progress in service.download_playlist(url):
            ...     if progress.phase == "extracting":
            ...         print(f"Extracting: {progress.current}/{progress.total}")
            ...     elif progress.phase == "downloading":
            ...         result = progress.download_progress.result
            ...         print(f"Downloaded: {result.track.title}")
        """
        tracks: list[TrackMetadata] = []
        playlist_info: PlaylistInfo | None = None

        # Phase 1: Extract metadata
        logger.info("Phase 1: Extracting metadata from %s", url)
        for progress in self._extractor.extract(url):
            tracks.append(progress.track)
            playlist_info = progress.playlist_info
            yield PlaylistProgress(
                phase="extracting",
                current=progress.current,
                total=progress.total,
                extract_progress=progress,
            )

        if not tracks or not playlist_info:
            logger.warning("No tracks extracted, nothing to download")
            self._last_result = None
            return

        logger.info("Extracted %d tracks from playlist", len(tracks))

        # Phase 2: Download tracks
        logger.info("Phase 2: Downloading %d tracks", len(tracks))
        results: list[DownloadResult] = []
        for progress in self._downloader.download_tracks(tracks):
            results.append(progress.result)
            yield PlaylistProgress(
                phase="downloading",
                current=progress.current,
                total=progress.total,
                download_progress=progress,
            )

        logger.info(
            "Downloads complete: %d success, %d skipped, %d failed",
            sum(1 for r in results if r.status.value == "success"),
            sum(1 for r in results if r.status.value == "skipped"),
            sum(1 for r in results if r.status.value == "failed"),
        )

        # Phase 3: Compose playlist artifacts
        logger.info("Phase 3: Generating playlist files")
        yield PlaylistProgress(
            phase="composing",
            current=0,
            total=1,
            message="Generating playlist files...",
        )

        m3u_path, cover_path = self._composer.compose(
            self._config.download.base_path,
            playlist_info,
            results,
            generate_m3u=self._config.generate_m3u,
            save_cover=self._config.save_cover,
            skip_album_m3u=self._config.skip_album_m3u,
        )

        yield PlaylistProgress(
            phase="composing",
            current=1,
            total=1,
            message="Done",
        )

        # Store result for retrieval
        self._last_result = PlaylistDownloadResult(
            playlist_info=playlist_info,
            download_results=results,
            m3u_path=m3u_path,
            cover_path=cover_path,
        )

        logger.info("Playlist download complete")

    def download_playlist_all(self, url: str) -> PlaylistDownloadResult:
        """Download a playlist and return the complete result.

        Convenience method that consumes the iterator and returns the result.
        Use download_playlist() if you need progress updates.

        Args:
            url: YouTube Music playlist URL.

        Returns:
            Complete playlist download result.

        Raises:
            ValueError: If the download yields no result (empty playlist).

        Example:
            >>> result = service.download_playlist_all(url)
            >>> print(f"Downloaded {result.success_count} tracks")
            >>> print(f"M3U saved to: {result.m3u_path}")
        """
        # Consume iterator
        for _ in self.download_playlist(url):
            pass

        if self._last_result is None:
            raise ValueError("No tracks found in playlist")

        return self._last_result

    def get_result(self) -> PlaylistDownloadResult | None:
        """Get the result of the last download operation.

        Returns:
            The last download result, or None if no download has completed.
        """
        return self._last_result
