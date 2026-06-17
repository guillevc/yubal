"""YouTube Music API client wrapper."""

import logging
from collections import OrderedDict
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol, cast

from ytmusicapi import YTMusic
from ytmusicapi.auth.types import AuthType
from ytmusicapi.exceptions import YTMusicError, YTMusicServerError, YTMusicUserError

from yubal.config import APIConfig
from yubal.exceptions import (
    AuthenticationRequiredError,
    PlaylistNotFoundError,
    TrackNotFoundError,
    UnsupportedPlaylistError,
    UpstreamAPIError,
    YubalError,
)
from yubal.models.enums import SkipReason
from yubal.models.ytmusic import Album, Playlist, PlaylistTrack, SearchResult
from yubal.utils.cookies import cookies_to_ytmusic_auth

logger = logging.getLogger(__name__)

# Maximum number of albums to cache per client instance
_ALBUM_CACHE_SIZE = 128

# Special playlist ID for the user's "Liked Music" pseudo-playlist on
# YouTube Music. Requires authentication and has no real title in the API
# response, so we substitute a sensible default.
_LIKED_MUSIC_ID = "LM"
_LIKED_MUSIC_TITLE = "Liked Music"


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

    def get_track(self, video_id: str) -> PlaylistTrack:
        """Fetch a single track by video ID."""
        ...

    def get_upload_year(self, video_id: str) -> str | None:
        """Return the YouTube upload year (YYYY) for a video, or None."""
        ...

    def get_lyrics_browse_id(self, video_id: str) -> str | None:
        """Return the lyrics browseId (MPLYt...) for a video, or None."""
        ...

    def get_lyrics(self, browse_id: str) -> Mapping[str, Any] | None:
        """Fetch lyrics payload by browseId (timestamps when available)."""
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
        # LRU cache for albums with size limit
        self._album_cache: OrderedDict[str, Album] = OrderedDict()

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
                logger.info("Using cookies for ytmusicapi requests")
                return YTMusic(auth=auth)
            logger.info("No valid cookies for ytmusicapi requests (missing SAPISID)")
            return YTMusic()

        logger.info("No cookies configured for ytmusicapi requests")
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
            UpstreamAPIError: If API request fails.
        """
        if not playlist_id or not playlist_id.strip():
            raise ValueError("playlist_id cannot be empty")

        # Check for unsupported playlist prefixes before making API call
        self._check_playlist_type(playlist_id)

        # The "Liked Music" pseudo-playlist is only accessible to the
        # authenticated user. Fail fast with a clear message instead of
        # letting ytmusicapi return a "Sign in" page that surfaces as a
        # confusing KeyError further down.
        if playlist_id == _LIKED_MUSIC_ID and not self._is_authenticated():
            raise AuthenticationRequiredError(
                "The Liked Music playlist (list=LM) requires authentication. "
                "Please upload your YouTube Music cookies via the web UI "
                "(Settings → upload cookies.txt) to access your liked songs."
            )

        logger.debug("Fetching playlist: %s", playlist_id)
        try:
            data = self._ytm.get_playlist(playlist_id, limit=None)
        except (YTMusicServerError, YTMusicUserError) as e:
            error_msg = str(e)
            logger.warning("YTMusic API error for playlist %s: %s", playlist_id, e)

            # Parse error to provide better error messages
            specific_error = self._parse_playlist_error(error_msg, playlist_id)
            if specific_error:
                raise specific_error from e

            raise UpstreamAPIError(f"Failed to fetch playlist: {e}") from e
        except YTMusicError as e:
            logger.warning("YTMusic error for playlist %s: %s", playlist_id, e)
            raise UpstreamAPIError(f"Failed to fetch playlist: {e}") from e
        except (KeyError, TypeError) as e:
            error_msg = str(e)
            logger.warning("Missing data in playlist response %s: %s", playlist_id, e)

            # Check if YouTube returned a "Sign in" page (auth failure)
            if isinstance(e, KeyError) and self._is_sign_in_response(error_msg):
                raise AuthenticationRequiredError(
                    "Authentication failed. YouTube returned a 'Sign in' page instead "
                    "of playlist data. Your cookies may be invalid, expired, or from "
                    "a non-authenticated session. Please re-export your cookies while "
                    "logged into YouTube Music."
                ) from e

            raise PlaylistNotFoundError(
                f"Playlist not found or malformed: {playlist_id}"
            ) from e

        if not data:
            raise PlaylistNotFoundError(f"Playlist not found: {playlist_id}")

        # The Liked Music response often has no title; provide a default
        # so downstream filenames and UI labels are sensible.
        if playlist_id == _LIKED_MUSIC_ID and not data.get("title"):
            data["title"] = _LIKED_MUSIC_TITLE

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
                valid_tracks.append(self._normalize_playlist_track(track))

        data["tracks"] = valid_tracks
        data["unavailable_tracks"] = unavailable_tracks

        logger.debug(
            "Fetched playlist with %d valid tracks (%d unavailable)",
            len(valid_tracks),
            len(unavailable_tracks),
        )
        return Playlist.model_validate(data)

    def _normalize_playlist_track(self, track: dict[str, Any]) -> dict[str, Any]:
        """Normalize playlist track fields before model validation."""
        normalized = dict(track)

        # ytmusicapi may return null for artists on some tracks.
        if normalized.get("artists") is None:
            normalized["artists"] = []

        return normalized

    def get_album(self, album_id: str) -> Album:
        """Fetch an album by ID.

        Results are cached with LRU eviction (max 128 albums).

        Args:
            album_id: YouTube Music album ID.

        Returns:
            Parsed Album model.

        Raises:
            UpstreamAPIError: If API request fails.
        """
        if album_id in self._album_cache:
            logger.debug("Album cache hit: %s", album_id)
            # Move to end (most recently used)
            self._album_cache.move_to_end(album_id)
            return self._album_cache[album_id]

        logger.debug("Fetching album: %s", album_id)
        try:
            data = self._ytm.get_album(album_id)
        except (YTMusicServerError, YTMusicUserError) as e:
            logger.warning("YTMusic API error for album %s: %s", album_id, e)
            raise UpstreamAPIError(f"Failed to fetch album: {e}") from e
        except YTMusicError as e:
            logger.warning("YTMusic error for album %s: %s", album_id, e)
            raise UpstreamAPIError(f"Failed to fetch album: {e}") from e

        album = Album.model_validate(data)

        # Add to cache with LRU eviction
        self._album_cache[album_id] = album
        if len(self._album_cache) > _ALBUM_CACHE_SIZE:
            # Remove oldest (first) item
            self._album_cache.popitem(last=False)

        return album

    def search_songs(self, query: str) -> list[SearchResult]:
        """Search for songs.

        Args:
            query: Search query string.

        Returns:
            List of parsed SearchResult models.

        Raises:
            UpstreamAPIError: If API request fails.
        """
        logger.debug("Searching songs: %s", query)
        try:
            data = self._ytm.search(
                query,
                filter="songs",
                limit=self._config.search_limit,
                ignore_spelling=self._config.ignore_spelling,
            )
        except (YTMusicServerError, YTMusicUserError) as e:
            logger.warning("YTMusic API error for search '%s': %s", query, e)
            raise UpstreamAPIError(f"Search failed: {e}") from e
        except YTMusicError as e:
            logger.warning("YTMusic error for search '%s': %s", query, e)
            raise UpstreamAPIError(f"Search failed: {e}") from e

        return [SearchResult.model_validate(r) for r in data]

    def get_track(self, video_id: str) -> PlaylistTrack:
        """Fetch a single track by video ID using get_watch_playlist().

        Args:
            video_id: YouTube video ID.

        Returns:
            Parsed PlaylistTrack model.

        Raises:
            ValueError: If video_id is empty.
            TrackNotFoundError: If track doesn't exist or is inaccessible.
            UpstreamAPIError: If API request fails.
        """
        if not video_id or not video_id.strip():
            raise ValueError("video_id cannot be empty")

        logger.debug("Fetching track: %s", video_id)
        try:
            data = self._ytm.get_watch_playlist(video_id)
        except (YTMusicServerError, YTMusicUserError) as e:
            logger.warning("YTMusic API error for track %s: %s", video_id, e)
            raise UpstreamAPIError(f"Failed to fetch track: {e}") from e
        except YTMusicError as e:
            logger.warning("YTMusic error for track %s: %s", video_id, e)
            raise UpstreamAPIError(f"Failed to fetch track: {e}") from e

        tracks = cast(list[dict[str, Any]], data.get("tracks") or [])
        if not tracks:
            raise TrackNotFoundError(f"Track not found: {video_id}")

        track_data = self._normalize_watch_track(tracks[0])
        return PlaylistTrack.model_validate(track_data)

    def get_upload_year(self, video_id: str) -> str | None:
        """Return the YouTube upload year (e.g. "2021") for a video, or None.

        Used as a release-year fallback for tracks with no album match, where
        YouTube Music provides no album-level release year. Reads ``uploadDate``
        (falling back to ``publishDate``) from ``get_song()``'s microformat and
        keeps the leading four-digit year.

        Best-effort: all upstream errors are swallowed at DEBUG and return None.

        Args:
            video_id: YouTube video ID.

        Returns:
            Four-digit upload year string, or None if unavailable.
        """
        if not video_id or not video_id.strip():
            return None

        try:
            data = self._ytm.get_song(video_id)
        except (YTMusicError, KeyError, TypeError) as e:
            logger.debug("YT Music get_song failed for %s: %s", video_id, e)
            return None

        if not isinstance(data, Mapping):
            return None
        microformat = data.get("microformat")
        renderer = (
            microformat.get("microformatDataRenderer")
            if isinstance(microformat, Mapping)
            else None
        )
        if not isinstance(renderer, Mapping):
            return None

        upload_date = renderer.get("uploadDate") or renderer.get("publishDate")
        if not isinstance(upload_date, str) or len(upload_date) < 4:
            return None
        year = upload_date[:4]
        return year if year.isdigit() else None

    def get_lyrics_browse_id(self, video_id: str) -> str | None:
        """Return the lyrics browseId (`MPLYt...`) for a video, or None.

        Calls `get_watch_playlist` and extracts the `lyrics` field, which
        holds the browseId required by `get_lyrics`. Best-effort: all
        upstream errors are swallowed (logged at DEBUG) and return None.

        Args:
            video_id: YouTube video ID.

        Returns:
            The lyrics browseId if available, None otherwise.
        """
        if not video_id or not video_id.strip():
            return None

        try:
            data = self._ytm.get_watch_playlist(video_id)
        except (YTMusicError, KeyError, TypeError) as e:
            logger.debug("YT Music watch_playlist failed for %s: %s", video_id, e)
            return None

        browse_id = data.get("lyrics") if isinstance(data, dict) else None
        return browse_id if isinstance(browse_id, str) and browse_id else None

    def get_lyrics(self, browse_id: str) -> Mapping[str, Any] | None:
        """Fetch a lyrics payload by browseId.

        Wraps `ytmusicapi.YTMusic.get_lyrics(browse_id, timestamps=True)`.
        Returns the raw dict (with keys `lyrics`, `source`, `hasTimestamps`).
        Best-effort: all upstream errors are swallowed at DEBUG, returns None.

        Args:
            browse_id: Lyrics browseId from `get_lyrics_browse_id`.

        Returns:
            Raw lyrics payload dict, or None on error / no data.
        """
        if not browse_id or not browse_id.strip():
            return None

        try:
            payload = self._ytm.get_lyrics(browse_id, timestamps=True)
        except (YTMusicError, KeyError, TypeError) as e:
            logger.debug("YT Music get_lyrics failed for %s: %s", browse_id, e)
            return None

        if not isinstance(payload, Mapping):
            return None
        return payload

    def _normalize_watch_track(self, track: dict) -> dict:
        """Normalize get_watch_playlist track to PlaylistTrack format.

        The get_watch_playlist API returns tracks with different field names:
        - 'thumbnail' instead of 'thumbnails'
        - 'length' (string) instead of 'duration_seconds' (int)
        """
        result = dict(track)

        # Normalize thumbnail -> thumbnails
        if "thumbnail" in result and "thumbnails" not in result:
            result["thumbnails"] = result.pop("thumbnail")

        # Normalize length -> duration_seconds
        if "length" in result and "duration_seconds" not in result:
            result["duration_seconds"] = self._parse_duration(result.pop("length"))

        return result

    def _parse_duration(self, length: str) -> int:
        """Parse duration string like '3:00' or '1:23:45' to seconds.

        Returns 0 for unparseable formats (logs warning).
        """
        if not length:
            return 0

        try:
            parts = length.split(":")
            if len(parts) == 2:
                minutes, seconds = int(parts[0]), int(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:
                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            logger.warning("Unexpected duration format: %s", length)
            return 0
        except ValueError:
            logger.warning("Could not parse duration: %s", length)
            return 0

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

    def _is_authenticated(self) -> bool:
        """Whether the underlying YTMusic client has auth credentials.

        Mirrors ytmusicapi's own auth check (``YTMusic._check_auth``) so we
        can fail fast on endpoints that require login, like Liked Music.
        Test code may inject a mock client; mocks won't expose an AuthType
        and are treated as authenticated.
        """
        auth_type = getattr(self._ytm, "auth_type", None)
        if auth_type is None:
            return True
        try:
            return auth_type != AuthType.UNAUTHORIZED
        except TypeError:
            return True

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

    def _is_sign_in_response(self, error_msg: str) -> bool:
        """Check if error indicates YouTube returned a 'Sign in' page.

        When cookies are invalid/expired, YouTube returns a page asking the user
        to sign in instead of the expected playlist data. ytmusicapi then raises
        a KeyError because expected fields are missing.

        Args:
            error_msg: Error message from ytmusicapi KeyError.

        Returns:
            True if error indicates auth failure (sign-in page returned).
        """
        # These patterns indicate YouTube returned a sign-in page
        sign_in_indicators = [
            "'Sign in'",
            "Sign in to listen",
            "signInEndpoint",
            "singleColumnBrowseResultsRenderer",  # Used for sign-in pages
        ]
        return any(indicator in error_msg for indicator in sign_in_indicators)

    def _parse_playlist_error(
        self, error_msg: str, playlist_id: str
    ) -> YubalError | None:
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
