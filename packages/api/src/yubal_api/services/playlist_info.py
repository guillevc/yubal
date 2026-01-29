"""Service for fetching playlist information from YouTube Music."""

from pathlib import Path

from yubal.client import YTMusicClient
from yubal.utils.url import parse_playlist_id


class PlaylistInfoService:
    """Service to fetch playlist metadata from YouTube Music."""

    def __init__(self, cookies_path: Path | None = None) -> None:
        """Initialize the service.

        Args:
            cookies_path: Optional path to cookies.txt for authenticated requests.
        """
        self._client = YTMusicClient(cookies_path=cookies_path)

    def get_playlist_title(self, url: str) -> str:
        """Get the title of a playlist from its URL.

        Args:
            url: YouTube Music playlist URL.

        Returns:
            The playlist title.

        Raises:
            PlaylistParseError: If URL cannot be parsed (400).
            PlaylistNotFoundError: If playlist doesn't exist (404).
            AuthenticationRequiredError: If authentication is required (401).
            UnsupportedPlaylistError: If playlist type is not supported (422).
            APIError: If API request fails (502).
        """
        playlist_id = parse_playlist_id(url)
        playlist = self._client.get_playlist(playlist_id)
        return playlist.title or "Unknown Playlist"
