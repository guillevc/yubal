"""Custom exceptions for yubal.

All exceptions include an HTTP status_code attribute for easy
integration with web frameworks like FastAPI.
"""


class YTMetaError(Exception):
    """Base exception for yubal.

    Attributes:
        status_code: HTTP status code for API error responses.
    """

    status_code: int = 500

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class PlaylistParseError(YTMetaError):
    """Failed to parse playlist URL.

    Raised when the provided URL doesn't contain a valid playlist ID.
    """

    status_code: int = 400  # Bad Request


class SongParseError(YTMetaError):
    """Failed to parse song URL.

    Raised when the provided URL doesn't contain a valid video ID.
    """

    status_code: int = 400  # Bad Request


class UnsupportedVideoTypeError(YTMetaError):
    """Video type is not supported for download.

    Raised when trying to download a video that is not an ATV (Audio Track Video)
    or OMV (Official Music Video), such as UGC (User Generated Content).
    """

    status_code: int = 400  # Bad Request


class PlaylistNotFoundError(YTMetaError):
    """Playlist not found or inaccessible.

    Raised when the playlist doesn't exist or is private.
    """

    status_code: int = 404  # Not Found


class AuthenticationRequiredError(YTMetaError):
    """Authentication required to access this playlist.

    Raised when trying to access a private playlist without valid cookies.
    """

    status_code: int = 401  # Unauthorized


class UnsupportedPlaylistError(YTMetaError):
    """Playlist type is not supported.

    Raised for auto-generated playlists like Recap, Discover Mix, etc.
    that use a different API structure not supported by ytmusicapi.
    """

    status_code: int = 400  # Bad Request


class APIError(YTMetaError):
    """YouTube Music API error.

    Raised when the underlying API request fails.
    """

    status_code: int = 502  # Bad Gateway (upstream failure)


class DownloadError(YTMetaError):
    """Failed to download a track.

    Raised when yt-dlp fails to download audio.
    """

    status_code: int = 500  # Internal Server Error


class CancellationError(YTMetaError):
    """Operation was cancelled.

    Raised when a download or extraction operation is cancelled
    via a CancelToken.
    """

    status_code: int = 499  # Client Closed Request (nginx convention)
