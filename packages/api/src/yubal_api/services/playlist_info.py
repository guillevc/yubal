"""Service for fetching playlist information from YouTube Music."""

from dataclasses import dataclass
from pathlib import Path

from yubal import parse_playlist_id
from yubal.client import YTMusicClient


@dataclass(frozen=True)
class PlaylistMetadata:
    """Metadata about a playlist."""

    title: str
    thumbnail_url: str | None


class PlaylistInfoService:
    """Service to fetch playlist metadata from YouTube Music."""

    def __init__(self, cookies_path: Path | None = None) -> None:
        """Initialize the service.

        Args:
            cookies_path: Optional path to cookies.txt for authenticated requests.
        """
        self._client = YTMusicClient(cookies_path=cookies_path)

    def get_playlist_metadata(self, url: str) -> PlaylistMetadata:
        """Get the metadata of a playlist from its URL.

        Args:
            url: YouTube Music playlist URL.

        Returns:
            PlaylistMetadata containing title and thumbnail URL.

        Raises:
            PlaylistParseError: If URL cannot be parsed (400).
            PlaylistNotFoundError: If playlist doesn't exist (404).
            AuthenticationRequiredError: If authentication is required (401).
            UnsupportedPlaylistError: If playlist type is not supported (422).
            APIError: If API request fails (502).
        """
        playlist_id = parse_playlist_id(url)
        playlist = self._client.get_playlist(playlist_id)
        title = playlist.title or "Unknown Playlist"
        thumbnail_url = playlist.thumbnails[-1].url if playlist.thumbnails else None
        return PlaylistMetadata(title=title, thumbnail_url=thumbnail_url)
