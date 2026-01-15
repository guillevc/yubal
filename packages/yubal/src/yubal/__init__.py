"""yubal - Extract metadata from YouTube Music playlists.

This library provides tools for extracting structured metadata from
YouTube Music playlists, including track information, album details,
and artist data. It also supports downloading tracks using yt-dlp.

Designed for use as a library in applications (e.g., FastAPI) with
a CLI for debugging and development.

Example:
    >>> from yubal import create_extractor
    >>> extractor = create_extractor()
    >>> tracks = extractor.extract("https://music.youtube.com/playlist?list=...")
    >>> for track in tracks:
    ...     print(f"{track.artist} - {track.title}")

For downloading tracks:
    >>> from yubal import DownloadService, DownloadConfig
    >>> config = DownloadConfig(base_path=Path("./music"))
    >>> downloader = DownloadService(config)
    >>> results = downloader.download_tracks(tracks)
"""

from pathlib import Path

from yubal.client import YTMusicClient, YTMusicProtocol
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
    ExtractProgress,
    TrackMetadata,
    VideoType,
)
from yubal.services import (
    DownloaderProtocol,
    DownloadProgress,
    DownloadResult,
    DownloadService,
    DownloadStatus,
    MetadataExtractorService,
    PlaylistComposerService,
    PlaylistDownloadResult,
    PlaylistDownloadService,
    PlaylistInfo,
    PlaylistProgress,
    YTDLPDownloader,
    tag_track,
)
from yubal.utils import clear_cover_cache, fetch_cover

__version__ = "0.1.0"


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

    Example:
        >>> extractor = create_extractor()
        >>> tracks = extractor.extract(playlist_url)

        # With custom config
        >>> config = APIConfig(search_limit=3)
        >>> extractor = create_extractor(config)

        # With authentication
        >>> extractor = create_extractor(cookies_path=Path("cookies.txt"))
    """
    client = YTMusicClient(config=config, cookies_path=cookies_path)
    return MetadataExtractorService(client)


def create_downloader(config: DownloadConfig) -> DownloadService:
    """Create a configured download service.

    This is the recommended way to create a downloader for library usage.

    Args:
        config: Download configuration (base_path is required).

    Returns:
        A configured DownloadService instance.

    Example:
        >>> config = DownloadConfig(base_path=Path("./music"))
        >>> downloader = create_downloader(config)
        >>> results = downloader.download_tracks(tracks)

        # With custom codec
        >>> config = DownloadConfig(base_path=Path("./music"), codec=AudioCodec.MP3)
        >>> downloader = create_downloader(config)
    """
    return DownloadService(config)


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

    Example:
        >>> config = PlaylistDownloadConfig(
        ...     download=DownloadConfig(base_path=Path("./music"))
        ... )
        >>> service = create_playlist_downloader(config)
        >>>
        >>> # With progress updates
        >>> for progress in service.download_playlist(url):
        ...     print(f"[{progress.phase}] {progress.current}/{progress.total}")
        >>> result = service.get_result()
        >>>
        >>> # Or all at once
        >>> result = service.download_playlist_all(url)
        >>> print(f"Downloaded: {result.success_count}")
        >>> print(f"M3U: {result.m3u_path}")

        # With authentication for private playlists
        >>> service = create_playlist_downloader(config, cookies_path=cookies)
    """
    return PlaylistDownloadService(config, cookies_path=cookies_path)


__all__ = [
    "APIConfig",
    "APIError",
    "AudioCodec",
    "AuthenticationRequiredError",
    "CancelToken",
    "CancellationError",
    "ContentKind",
    "DownloadConfig",
    "DownloadError",
    "DownloadProgress",
    "DownloadResult",
    "DownloadService",
    "DownloadStatus",
    "DownloaderProtocol",
    "ExtractProgress",
    "MetadataExtractorService",
    "PlaylistComposerService",
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
    "YTDLPDownloader",
    "YTMetaError",
    "YTMusicClient",
    "YTMusicProtocol",
    "clear_cover_cache",
    "create_downloader",
    "create_extractor",
    "create_playlist_downloader",
    "fetch_cover",
    "tag_track",
]
