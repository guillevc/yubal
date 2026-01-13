"""YouTube Music API client wrapper."""

import logging
from typing import Protocol

from ytmusicapi import YTMusic

from ytmeta.config import APIConfig
from ytmeta.exceptions import APIError, PlaylistNotFoundError
from ytmeta.models.ytmusic import Album, Playlist, SearchResult

logger = logging.getLogger(__name__)


class YTMusicProtocol(Protocol):
    """Protocol for YouTube Music API clients.

    This protocol enables dependency injection and testing.
    Implement this protocol to create mock clients for testing.
    """

    def get_playlist(self, playlist_id: str) -> Playlist:
        """Fetch a playlist by ID."""
        ...

    def get_album(self, album_id: str) -> Album:
        """Fetch an album by ID."""
        ...

    def search_songs(self, query: str) -> list[SearchResult]:
        """Search for songs."""
        ...


class YTMusicClient:
    """Production YouTube Music API client.

    Wraps ytmusicapi with consistent error handling and response parsing.
    Implements YTMusicProtocol for type safety.
    """

    def __init__(
        self,
        ytmusic: YTMusic | None = None,
        config: APIConfig | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            ytmusic: Optional YTMusic instance. Creates one if not provided.
            config: Optional API configuration. Uses defaults if not provided.
        """
        self._ytm = ytmusic or YTMusic()
        self._config = config or APIConfig()
        self._album_cache: dict[str, Album] = {}

    def get_playlist(self, playlist_id: str) -> Playlist:
        """Fetch a playlist by ID.

        Args:
            playlist_id: YouTube Music playlist ID.

        Returns:
            Parsed Playlist model.

        Raises:
            ValueError: If playlist_id is empty.
            PlaylistNotFoundError: If playlist doesn't exist or is inaccessible.
            APIError: If API request fails.
        """
        if not playlist_id or not playlist_id.strip():
            raise ValueError("playlist_id cannot be empty")

        logger.debug("Fetching playlist: %s", playlist_id)
        try:
            data = self._ytm.get_playlist(playlist_id, limit=None)
        except Exception as e:
            logger.error("Failed to fetch playlist %s: %s", playlist_id, e)
            raise APIError(f"Failed to fetch playlist: {e}") from e

        if not data:
            raise PlaylistNotFoundError(f"Playlist not found: {playlist_id}")

        # Filter out unavailable tracks (no videoId) before validation
        raw_tracks = data.get("tracks") or []
        valid_tracks = [t for t in raw_tracks if t and t.get("videoId")]
        unavailable_count = len(raw_tracks) - len(valid_tracks)

        data["tracks"] = valid_tracks
        data["unavailable_count"] = unavailable_count

        logger.debug(
            "Fetched playlist with %d valid tracks (%d unavailable)",
            len(valid_tracks),
            unavailable_count,
        )
        return Playlist.model_validate(data)

    def get_album(self, album_id: str) -> Album:
        """Fetch an album by ID.

        Results are cached for the lifetime of the client instance.

        Args:
            album_id: YouTube Music album ID.

        Returns:
            Parsed Album model.

        Raises:
            APIError: If API request fails.
        """
        if album_id in self._album_cache:
            logger.debug("Album cache hit: %s", album_id)
            return self._album_cache[album_id]

        logger.debug("Fetching album: %s", album_id)
        try:
            data = self._ytm.get_album(album_id)
        except Exception as e:
            logger.error("Failed to fetch album %s: %s", album_id, e)
            raise APIError(f"Failed to fetch album: {e}") from e

        album = Album.model_validate(data)
        self._album_cache[album_id] = album
        return album

    def search_songs(self, query: str) -> list[SearchResult]:
        """Search for songs.

        Args:
            query: Search query string.

        Returns:
            List of parsed SearchResult models.

        Raises:
            APIError: If API request fails.
        """
        logger.debug("Searching songs: %s", query)
        try:
            data = self._ytm.search(
                query,
                filter="songs",
                limit=self._config.search_limit,
                ignore_spelling=self._config.ignore_spelling,
            )
        except Exception as e:
            logger.error("Search failed for '%s': %s", query, e)
            raise APIError(f"Search failed: {e}") from e

        return [SearchResult.model_validate(r) for r in data]

    def clear_album_cache(self) -> None:
        """Clear the album cache."""
        self._album_cache.clear()
        logger.debug("Album cache cleared")

    def get_album_cache_size(self) -> int:
        """Get the number of cached albums.

        Returns:
            Number of album IDs currently cached.
        """
        return len(self._album_cache)
