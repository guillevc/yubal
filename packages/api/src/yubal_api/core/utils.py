"""URL parsing and detection utilities."""

import re


def extract_playlist_id(url: str) -> str | None:
    """Extract playlist ID from YouTube Music URL.

    Args:
        url: YouTube Music URL (e.g., https://music.youtube.com/playlist?list=PLxxx)

    Returns:
        Playlist ID or None if not found
    """
    match = re.search(r"list=([^&]+)", url)
    return match.group(1) if match else None
