"""Custom exceptions for ytmeta.

All exceptions include an HTTP status_code attribute for easy
integration with web frameworks like FastAPI.
"""


class YTMetaError(Exception):
    """Base exception for ytmeta.

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


class PlaylistNotFoundError(YTMetaError):
    """Playlist not found or inaccessible.

    Raised when the playlist doesn't exist or is private.
    """

    status_code: int = 404  # Not Found


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
