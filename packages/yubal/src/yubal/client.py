"""YouTube Music API client wrapper."""

import logging
from pathlib import Path
from typing import Protocol

from ytmusicapi import YTMusic

from yubal.config import APIConfig
from yubal.exceptions import (
    APIError,
    AuthenticationRequiredError,
    PlaylistNotFoundError,
    UnsupportedPlaylistError,
    YTMetaError,
)
from yubal.models.domain import SkipReason
from yubal.models.ytmusic import Album, Playlist, SearchResult
from yubal.utils.cookies import cookies_to_ytmusic_auth

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
        cookies_path: Path | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            ytmusic: Optional YTMusic instance. Creates one if not provided.
            config: Optional API configuration. Uses defaults if not provided.
            cookies_path: Optional path to cookies.txt for authentication.
                         If provided and valid, enables authenticated requests.
        """
        if ytmusic:
            self._ytm = ytmusic
        else:
            self._ytm = self._create_ytmusic(cookies_path)
        self._config = config or APIConfig()
        self._album_cache: dict[str, Album] = {}

    def _create_ytmusic(self, cookies_path: Path | None) -> YTMusic:
        """Create YTMusic instance with optional authentication.

        Args:
            cookies_path: Optional path to cookies.txt file.

        Returns:
            Configured YTMusic instance.
        """
        if cookies_path:
            auth = cookies_to_ytmusic_auth(cookies_path)
            if auth:
                logger.info("Using authenticated YTMusic client")
                return YTMusic(auth=auth)
            logger.debug("Cookies file invalid or missing SAPISID, using anonymous")

        logger.debug("Using anonymous YTMusic client")
        return YTMusic()

    def get_playlist(self, playlist_id: str) -> Playlist:
        """Fetch a playlist by ID.

        Args:
            playlist_id: YouTube Music playlist ID.

        Returns:
            Parsed Playlist model.

        Raises:
            ValueError: If playlist_id is empty.
            PlaylistNotFoundError: If playlist doesn't exist or is inaccessible.
            AuthenticationRequiredError: If playlist requires authentication.
            UnsupportedPlaylistError: If playlist type is not supported.
            APIError: If API request fails.
        """
        if not playlist_id or not playlist_id.strip():
            raise ValueError("playlist_id cannot be empty")

        # Check for unsupported playlist prefixes before making API call
        self._check_playlist_type(playlist_id)

        logger.debug("Fetching playlist: %s", playlist_id)
        try:
            data = self._ytm.get_playlist(playlist_id, limit=None)
        except Exception as e:
            error_msg = str(e)
            logger.exception("Failed to fetch playlist %s: %s", playlist_id, e)

            # Parse error to provide better error messages
            specific_error = self._parse_playlist_error(error_msg, playlist_id)
            if specific_error:
                raise specific_error from e

            raise APIError(f"Failed to fetch playlist: {e}") from e

        if not data:
            raise PlaylistNotFoundError(f"Playlist not found: {playlist_id}")

        # Categorize tracks: available vs unavailable with reasons
        raw_tracks = data.get("tracks") or []
        valid_tracks: list[dict] = []
        unavailable_tracks: list[dict] = []

        for track in raw_tracks:
            if not track:
                continue

            video_id = track.get("videoId")
            is_available = track.get("isAvailable", True)

            # Extract metadata for display
            title = track.get("title")
            artists = [
                name for a in (track.get("artists") or []) if (name := a.get("name"))
            ]
            album_info = track.get("album")
            album_name = (
                album_info.get("name") if isinstance(album_info, dict) else None
            )

            if not video_id:
                unavailable_tracks.append(
                    {
                        "title": title,
                        "artists": artists,
                        "album": album_name,
                        "reason": SkipReason.NO_VIDEO_ID.value,
                    }
                )
            elif not is_available:
                unavailable_tracks.append(
                    {
                        "title": title,
                        "artists": artists,
                        "album": album_name,
                        "reason": SkipReason.REGION_UNAVAILABLE.value,
                    }
                )
            else:
                valid_tracks.append(track)

        data["tracks"] = valid_tracks
        data["unavailable_tracks"] = unavailable_tracks

        logger.debug(
            "Fetched playlist with %d valid tracks (%d unavailable)",
            len(valid_tracks),
            len(unavailable_tracks),
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
            logger.exception("Failed to fetch album %s: %s", album_id, e)
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
            logger.exception("Search failed for '%s': %s", query, e)
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

    def _check_playlist_type(self, playlist_id: str) -> None:
        """Check if playlist type is supported before fetching.

        Args:
            playlist_id: Playlist ID to check.

        Raises:
            UnsupportedPlaylistError: If playlist type is not supported.
        """
        # Known unsupported playlist prefixes (confirmed to fail)
        # Note: Many RD* prefixes (like RDTMAK) actually work fine
        unsupported_prefixes = {
            "LRSRK": "Recap playlists",  # Seasonal/yearly recaps
            "SE": "Episodes",  # Podcast episodes
        }

        for prefix, playlist_type in unsupported_prefixes.items():
            if playlist_id.startswith(prefix):
                raise UnsupportedPlaylistError(
                    f"{playlist_type} are auto-generated by YouTube Music and use "
                    "a different API format that is not supported. "
                    "Try saving the playlist to your library first."
                )

    def _parse_playlist_error(
        self, error_msg: str, playlist_id: str
    ) -> YTMetaError | None:
        """Parse ytmusicapi error to determine specific error type.

        Args:
            error_msg: Error message from ytmusicapi.
            playlist_id: The playlist ID that was requested.

        Returns:
            Specific exception if error type can be determined, None otherwise.
        """
        # Check for the "contents" KeyError which indicates empty/inaccessible playlist
        if "Unable to find 'contents'" not in error_msg:
            return None

        # Check if user is logged in by looking for logged_in value in error
        is_logged_in = "'logged_in', 'value': '1'" in error_msg

        # Check for noindex flag which indicates private/special playlist
        is_noindex = "'noindex': True" in error_msg

        if is_noindex:
            if is_logged_in:
                # User is authenticated but still can't access - unsupported type
                return UnsupportedPlaylistError(
                    "This playlist type is not supported. YouTube Music "
                    "auto-generated playlists (Recap, Discover Mix, etc.) use a "
                    "different API format. Try saving the playlist to your "
                    "library first, then use the saved copy."
                )
            else:
                # User is not authenticated - might be a private playlist
                return AuthenticationRequiredError(
                    "This playlist may be private and requires authentication. "
                    "Please upload your YouTube Music cookies via the web UI to "
                    "access private playlists. Go to Settings and upload a "
                    "cookies.txt file exported from your browser while logged "
                    "into YouTube Music."
                )

        # Generic case - playlist might be deleted or invalid
        if not is_logged_in:
            return AuthenticationRequiredError(
                "Unable to access playlist. This may be a private playlist that "
                "requires authentication. Please upload your YouTube Music "
                "cookies to access private content."
            )

        return None
