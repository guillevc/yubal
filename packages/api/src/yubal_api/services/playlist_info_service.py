"""Service for fetching playlist information from YouTube Music."""

import logging
from dataclasses import dataclass
from pathlib import Path

from yubal import ContentKind, parse_playlist_id
from yubal.client import YTMusicClient
from yubal.models.ytmusic import Playlist
from yubal.utils.url import parse_video_id

from yubal_api.domain.job import ContentInfo

logger = logging.getLogger(__name__)


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
            UpstreamAPIError: If API request fails (502).
        """
        playlist_id = parse_playlist_id(url)
        playlist = self._client.get_playlist(playlist_id)
        title = playlist.title or "Unknown Playlist"
        thumbnail_url = playlist.thumbnails[-1].url if playlist.thumbnails else None
        return PlaylistMetadata(title=title, thumbnail_url=thumbnail_url)

    def get_content_info(self, url: str) -> ContentInfo:
        """Get content info for any supported YouTube URL.

        Returns quick metadata (title, artist, kind, track count, year,
        thumbnail) from a single API call without running the full
        extraction pipeline.

        Args:
            url: YouTube Music URL (playlist, album, or single track).

        Returns:
            ContentInfo with metadata from the URL.

        Raises:
            PlaylistParseError: If URL cannot be parsed (400).
            TrackParseError: If single track URL is invalid (400).
            PlaylistNotFoundError: If playlist doesn't exist (404).
            TrackNotFoundError: If track doesn't exist (404).
            AuthenticationRequiredError: If authentication is required (401).
            UnsupportedPlaylistError: If playlist type is not supported (422).
            UpstreamAPIError: If API request fails (502).
        """
        video_id = parse_video_id(url)
        if video_id:
            return self._get_track_content_info(video_id, url)
        return self._get_playlist_content_info(url)

    def _get_playlist_content_info(self, url: str) -> ContentInfo:
        """Build ContentInfo from a playlist/album URL."""
        playlist_id = parse_playlist_id(url)
        playlist = self._client.get_playlist(playlist_id)

        kind, year = self._classify_and_get_year(playlist)

        return ContentInfo(
            title=playlist.title or "Unknown",
            artist=playlist.author.name if playlist.author else "Unknown Artist",
            year=year,
            track_count=len(playlist.tracks),
            playlist_id=playlist_id,
            url=url,
            thumbnail_url=(
                playlist.thumbnails[-1].url if playlist.thumbnails else None
            ),
            kind=kind,
        )

    def _classify_and_get_year(
        self, playlist: Playlist
    ) -> tuple[ContentKind, int | None]:
        """Classify playlist as album or playlist and extract year if album.

        Uses the same logic as the regular extraction flow:
        1. All tracks must reference the same album ID
        2. The album must be fetchable
        3. The playlist must contain all album tracks

        Returns:
            Tuple of (kind, year). Year is only set for confirmed albums.
        """
        if not playlist.tracks:
            return ContentKind.PLAYLIST, None

        # Check if all tracks reference the same album
        album_ids = {t.album.id for t in playlist.tracks if t.album and t.album.id}
        if len(album_ids) != 1:
            return ContentKind.PLAYLIST, None

        album_id = next(iter(album_ids))
        try:
            album = self._client.get_album(album_id)
        except Exception:
            logger.debug("Could not fetch album %s for classification", album_id)
            return ContentKind.PLAYLIST, None

        # Verify playlist contains all album tracks
        if len(playlist.tracks) != len(album.tracks):
            return ContentKind.PLAYLIST, None

        year = None
        if album.year:
            try:
                year = int(album.year)
            except ValueError:
                pass

        return ContentKind.ALBUM, year

    def _get_track_content_info(self, video_id: str, url: str) -> ContentInfo:
        """Build ContentInfo from a single track URL."""
        track = self._client.get_track(video_id)

        return ContentInfo(
            title=track.title,
            artist=(track.artists[0].name if track.artists else "Unknown Artist"),
            playlist_id=video_id,
            url=url,
            thumbnail_url=(track.thumbnails[-1].url if track.thumbnails else None),
            kind=ContentKind.TRACK,
        )
