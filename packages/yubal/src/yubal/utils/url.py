"""URL parsing utilities."""

import re
from enum import StrEnum

from yubal.exceptions import PlaylistParseError, SongParseError

PLAYLIST_ID_PATTERN = re.compile(r"list=([A-Za-z0-9_-]+)")
VIDEO_ID_PATTERN = re.compile(r"[?&]v=([A-Za-z0-9_-]+)")


class URLType(StrEnum):
    """Type of YouTube Music URL."""

    PLAYLIST = "playlist"
    SONG = "song"


def parse_playlist_id(url: str) -> str:
    """Extract playlist ID from YouTube Music URL.

    Args:
        url: Full YouTube Music playlist URL.

    Returns:
        The playlist ID string.

    Raises:
        PlaylistParseError: If playlist ID cannot be extracted.
    """
    if match := PLAYLIST_ID_PATTERN.search(url):
        return match.group(1)
    raise PlaylistParseError(f"Could not extract playlist ID from: {url}")


def parse_video_id(url: str) -> str:
    """Extract video ID from YouTube Music watch URL.

    Args:
        url: Full YouTube Music watch URL (e.g., https://music.youtube.com/watch?v=VIDEO_ID).

    Returns:
        The video ID string.

    Raises:
        SongParseError: If video ID cannot be extracted.
    """
    if match := VIDEO_ID_PATTERN.search(url):
        return match.group(1)
    raise SongParseError(f"Could not extract video ID from: {url}")


def detect_url_type(url: str) -> URLType:
    """Detect whether a URL is for a playlist or individual song.

    Args:
        url: YouTube Music URL.

    Returns:
        URLType.PLAYLIST for playlist/album URLs, URLType.SONG for watch URLs.

    Examples:
        >>> detect_url_type("https://music.youtube.com/playlist?list=PLxyz")
        URLType.PLAYLIST
        >>> detect_url_type("https://music.youtube.com/watch?v=abc123")
        URLType.SONG
    """
    # Check for watch URL (individual song)
    if "/watch?" in url and "v=" in url:
        return URLType.SONG
    # Otherwise assume it's a playlist/album URL
    return URLType.PLAYLIST
