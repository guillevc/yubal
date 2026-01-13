"""ytmeta - Extract metadata from YouTube Music playlists.

This library provides tools for extracting structured metadata from
YouTube Music playlists, including track information, album details,
and artist data. It also supports downloading tracks using yt-dlp.

Designed for use as a library in applications (e.g., FastAPI) with
a CLI for debugging and development.

Example:
    >>> from ytmeta import create_extractor
    >>> extractor = create_extractor()
    >>> tracks = extractor.extract("https://music.youtube.com/playlist?list=...")
    >>> for track in tracks:
    ...     print(f"{track.artist} - {track.title}")

For async usage (FastAPI):
    >>> tracks = await extractor.extract_async(url)

For downloading tracks:
    >>> from ytmeta import DownloadService, DownloadConfig
    >>> config = DownloadConfig(base_path=Path("./music"))
    >>> downloader = DownloadService(config)
    >>> results = downloader.download_tracks(tracks)
"""

from ytmeta.client import YTMusicClient, YTMusicProtocol
from ytmeta.config import APIConfig, AudioCodec, DownloadConfig, default_config
from ytmeta.exceptions import (
    AlbumNotFoundError,
    APIError,
    DownloadConfigError,
    DownloadError,
    PlaylistNotFoundError,
    PlaylistParseError,
    TrackExtractionError,
    YTMetaError,
)
from ytmeta.models.domain import TrackMetadata, VideoType
from ytmeta.services import (
    DownloaderProtocol,
    DownloadResult,
    DownloadService,
    DownloadStatus,
    MetadataExtractorService,
    YTDLPDownloader,
)

__version__ = "0.1.0"


def create_extractor(config: APIConfig | None = None) -> MetadataExtractorService:
    """Create a configured metadata extractor.

    This is the recommended way to create an extractor for library usage.
    It handles client instantiation internally.

    Args:
        config: Optional API configuration. Uses defaults if not provided.

    Returns:
        A configured MetadataExtractorService instance.

    Example:
        >>> extractor = create_extractor()
        >>> tracks = extractor.extract(playlist_url)

        # With custom config
        >>> config = APIConfig(search_limit=3)
        >>> extractor = create_extractor(config)
    """
    client = YTMusicClient(config=config)
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


__all__ = [
    "APIConfig",
    "APIError",
    "AlbumNotFoundError",
    "AudioCodec",
    "DownloadConfig",
    "DownloadConfigError",
    "DownloadError",
    "DownloadResult",
    "DownloadService",
    "DownloadStatus",
    "DownloaderProtocol",
    "MetadataExtractorService",
    "PlaylistNotFoundError",
    "PlaylistParseError",
    "TrackExtractionError",
    "TrackMetadata",
    "VideoType",
    "YTDLPDownloader",
    "YTMetaError",
    "YTMusicClient",
    "YTMusicProtocol",
    "create_downloader",
    "create_extractor",
    "default_config",
]
