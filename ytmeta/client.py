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

    def get_playlist(self, playlist_id: str) -> Playlist:
        """Fetch a playlist by ID.

        Args:
            playlist_id: YouTube Music playlist ID.

        Returns:
            Parsed Playlist model.

        Raises:
            PlaylistNotFoundError: If playlist doesn't exist or is inaccessible.
            APIError: If API request fails.
        """
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
        data["tracks"] = [t for t in raw_tracks if t and t.get("videoId")]

        logger.debug(
            "Fetched playlist with %d valid tracks", len(data.get("tracks", []))
        )
        return Playlist.model_validate(data)

    def get_album(self, album_id: str) -> Album:
        """Fetch an album by ID.

        Args:
            album_id: YouTube Music album ID.

        Returns:
            Parsed Album model.

        Raises:
            APIError: If API request fails.
        """
        logger.debug("Fetching album: %s", album_id)
        try:
            data = self._ytm.get_album(album_id)
        except Exception as e:
            logger.error("Failed to fetch album %s: %s", album_id, e)
            raise APIError(f"Failed to fetch album: {e}") from e

        return Album.model_validate(data)

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
