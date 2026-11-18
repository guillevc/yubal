"""Custom exceptions for yubal."""


class YubalError(Exception):
    """Base exception for yubal."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class PlaylistParseError(YubalError):
    """Failed to parse playlist URL.

    Raised when the provided URL doesn't contain a valid playlist ID.
    """


class TrackParseError(YubalError):
    """Failed to parse track URL.

    Raised when the provided URL doesn't contain a valid video ID,
    or when a playlist URL is provided instead of a single track URL.
    """


class PlaylistNotFoundError(YubalError):
    """Playlist not found or inaccessible.

    Raised when the playlist doesn't exist or is private.
    """


class TrackNotFoundError(YubalError):
    """Track not found or inaccessible.

    Raised when the track doesn't exist, has been removed, or is
    region-restricted and not available.
    """


class ArtistNotFoundError(YubalError):
    """Artist not found.

    Raised when an artist search has no results or the artist page
    doesn't exist.
    """


class AuthenticationRequiredError(YubalError):
    """Authentication required to access this playlist.

    Raised when trying to access a private playlist without valid cookies.
    """


class UnsupportedPlaylistError(YubalError):
    """Playlist type is not supported.

    Raised for auto-generated playlists like Recap, Discover Mix, etc.
    that use a different API structure not supported by ytmusicapi.
    """


class UpstreamAPIError(YubalError):
    """YouTube Music API error.

    Raised when the underlying API request fails.
    """


class DownloadError(YubalError):
    """Failed to download a track.

    Raised when yt-dlp fails to download audio.
    """


class CancellationError(YubalError):
    """Operation was cancelled.

    Raised when a download or extraction operation is cancelled
    via a CancelToken.
    """
