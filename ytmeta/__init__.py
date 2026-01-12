"""ytmeta - Extract metadata from YouTube Music playlists.

This library provides tools for extracting structured metadata from
YouTube Music playlists, including track information, album details,
and artist data.

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
"""

from ytmeta.client import YTMusicClient, YTMusicProtocol
from ytmeta.config import APIConfig, default_config
from ytmeta.exceptions import (
    AlbumNotFoundError,
    APIError,
    PlaylistNotFoundError,
    PlaylistParseError,
    TrackExtractionError,
    YTMetaError,
)
from ytmeta.models.domain import TrackMetadata, VideoType
from ytmeta.services import MetadataExtractorService

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


__all__ = [
    "APIConfig",
    "APIError",
    "AlbumNotFoundError",
    "MetadataExtractorService",
    "PlaylistNotFoundError",
    "PlaylistParseError",
    "TrackExtractionError",
    "TrackMetadata",
    "VideoType",
    "YTMetaError",
    "YTMusicClient",
    "YTMusicProtocol",
    "create_extractor",
    "default_config",
]
