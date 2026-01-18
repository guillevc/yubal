"""yubal - Extract metadata from YouTube Music playlists.

This library provides tools for extracting structured metadata from
YouTube Music playlists, including track information, album details,
and artist data. It also supports downloading tracks using yt-dlp.

Designed for use as a library in applications (e.g., FastAPI) with
a CLI for debugging and development.

Examples:
    Extract metadata from a playlist:
    ```python
    from yubal import create_extractor

    extractor = create_extractor()
    for progress in extractor.extract("https://music.youtube.com/playlist?list=..."):
        print(f"{progress.track.artist} - {progress.track.title}")
    ```

    Download a complete playlist:
    ```python
    from yubal import create_playlist_downloader, PlaylistDownloadConfig, DownloadConfig
    from pathlib import Path

    config = PlaylistDownloadConfig(download=DownloadConfig(base_path=Path("./music")))
    downloader = create_playlist_downloader(config)
    result = downloader.download_playlist_all(url)
    ```
"""

from pathlib import Path

# Internal imports (not exported)
from yubal.client import YTMusicClient as _YTMusicClient
from yubal.config import APIConfig, AudioCodec, DownloadConfig, PlaylistDownloadConfig
from yubal.exceptions import (
    APIError,
    AuthenticationRequiredError,
    CancellationError,
    DownloadError,
    PlaylistNotFoundError,
    PlaylistParseError,
    UnsupportedPlaylistError,
    YTMetaError,
)
from yubal.models.domain import (
    CancelToken,
    ContentKind,
    DownloadProgress,
    DownloadResult,
    DownloadStatus,
    ExtractProgress,
    PlaylistDownloadResult,
    PlaylistInfo,
    PlaylistProgress,
    TrackMetadata,
    VideoType,
)
from yubal.services import MetadataExtractorService, PlaylistDownloadService
from yubal.services.downloader import DownloadService as _DownloadService
from yubal.utils import clear_cover_cache, fetch_cover


def create_extractor(
    config: APIConfig | None = None,
    cookies_path: Path | None = None,
) -> MetadataExtractorService:
    """Create a configured metadata extractor.

    This is the recommended way to create an extractor for library usage.
    It handles client instantiation internally.

    Args:
        config: Optional API configuration. Uses defaults if not provided.
        cookies_path: Optional path to cookies.txt for YouTube Music authentication.
                     Enables access to private playlists when provided.

    Returns:
        A configured MetadataExtractorService instance.

    Examples:
        Basic usage:
        ```python
        extractor = create_extractor()
        tracks = extractor.extract(playlist_url)
        ```

        With custom config:
        ```python
        config = APIConfig(search_limit=3)
        extractor = create_extractor(config)
        ```

        With authentication:
        ```python
        extractor = create_extractor(cookies_path=Path("cookies.txt"))
        ```
    """
    client = _YTMusicClient(config=config, cookies_path=cookies_path)
    return MetadataExtractorService(client)


def create_downloader(config: DownloadConfig) -> _DownloadService:
    """Create a configured download service.

    This is the recommended way to create a downloader for library usage.

    Args:
        config: Download configuration (base_path is required).

    Returns:
        A configured DownloadService instance.

    Examples:
        Basic usage:
        ```python
        config = DownloadConfig(base_path=Path("./music"))
        downloader = create_downloader(config)
        results = downloader.download_tracks(tracks)
        ```

        With custom codec:
        ```python
        config = DownloadConfig(base_path=Path("./music"), codec=AudioCodec.MP3)
        downloader = create_downloader(config)
        ```
    """
    return _DownloadService(config)


def create_playlist_downloader(
    config: PlaylistDownloadConfig,
    cookies_path: Path | None = None,
) -> PlaylistDownloadService:
    """Create a configured playlist download service.

    This is the recommended way to download complete playlists. It handles
    the full workflow: metadata extraction, downloading, and M3U/cover generation.

    Args:
        config: Playlist download configuration.
        cookies_path: Optional path to cookies.txt for YouTube Music authentication.
                     Enables access to private playlists when provided.

    Returns:
        A configured PlaylistDownloadService instance.

    Examples:
        With progress updates:
        ```python
        config = PlaylistDownloadConfig(
            download=DownloadConfig(base_path=Path("./music"))
        )
        service = create_playlist_downloader(config)
        for progress in service.download_playlist(url):
            print(f"[{progress.phase}] {progress.current}/{progress.total}")
        result = service.get_result()
        ```

        Download all at once:
        ```python
        result = service.download_playlist_all(url)
        print(f"Downloaded: {result.success_count}")
        ```

        With authentication:
        ```python
        service = create_playlist_downloader(config, cookies_path=Path("cookies.txt"))
        ```
    """
    return PlaylistDownloadService(config, cookies_path=cookies_path)


__all__ = [
    # Configuration
    "APIConfig",
    # Exceptions
    "APIError",
    "AudioCodec",
    "AuthenticationRequiredError",
    # Domain models
    "CancelToken",
    "CancellationError",
    "ContentKind",
    "DownloadConfig",
    "DownloadError",
    "DownloadProgress",
    "DownloadResult",
    "DownloadStatus",
    "ExtractProgress",
    # Services
    "MetadataExtractorService",
    "PlaylistDownloadConfig",
    "PlaylistDownloadResult",
    "PlaylistDownloadService",
    "PlaylistInfo",
    "PlaylistNotFoundError",
    "PlaylistParseError",
    "PlaylistProgress",
    "TrackMetadata",
    "UnsupportedPlaylistError",
    "VideoType",
    "YTMetaError",
    # Utilities
    "clear_cover_cache",
    # Factory functions (recommended entry points)
    "create_downloader",
    "create_extractor",
    "create_playlist_downloader",
    "fetch_cover",
]
