"""Filename sanitization utilities for safe filesystem paths."""

from pathlib import Path

from pathvalidate import sanitize_filename


def clean_filename(s: str) -> str:
    """Sanitize a string for use in a filename.

    Converts unicode characters to ASCII equivalents and removes
    or replaces characters that are invalid in filenames.

    Args:
        s: String to sanitize.

    Returns:
        Sanitized string safe for use in filenames.

    Example:
        >>> clean_filename("Bjork - Joga")
        'Bjork - Joga'
        >>> clean_filename("AC/DC")
        'ACDC'
    """
    return sanitize_filename(s)


def format_playlist_filename(playlist_name: str, playlist_id: str) -> str:
    """Format playlist filename with ID suffix to avoid collisions.

    Args:
        playlist_name: Name of the playlist (will be sanitized).
        playlist_id: Unique playlist ID (last 8 chars used as suffix).

    Returns:
        Formatted filename without extension, e.g., "My Favorites [abcd1234]".
    """
    safe_name = clean_filename(playlist_name)
    if not safe_name or not safe_name.strip():
        safe_name = "Untitled Playlist"

    # Use last 8 chars of playlist_id (or full ID if shorter)
    id_suffix = playlist_id[-8:] if len(playlist_id) > 8 else playlist_id

    return f"{safe_name} [{id_suffix}]"


def build_track_path(
    base: Path,
    artist: str,
    year: str | None,
    album: str,
    track_number: int | None,
    title: str,
) -> Path:
    """Build a filesystem path for a track following the convention.

    Creates a path structure: base/Artist/YEAR - Album/NN - Title

    Args:
        base: Base directory for downloads.
        artist: Album artist name.
        year: Release year (or None for unknown).
        album: Album name.
        track_number: Track number (or None for unknown).
        title: Track title.

    Returns:
        Full path to the track file (without extension).

    Example:
        >>> build_track_path(Path("/music"), "Artist", "2024", "Album", 1, "Song")
        PosixPath('/music/Artist/2024 - Album/01 - Song')
    """
    # Sanitize components
    safe_artist = clean_filename(artist) or "Unknown Artist"
    safe_album = clean_filename(album) or "Unknown Album"
    safe_title = clean_filename(title) or "Unknown Track"

    # Build album folder name
    year_str = year or "0000"
    album_folder = f"{year_str} - {safe_album}"

    # Build track filename
    if track_number is not None:
        track_name = f"{track_number:02d} - {safe_title}"
    else:
        track_name = safe_title

    return base / safe_artist / album_folder / track_name


def build_unmatched_track_path(
    base: Path,
    artist: str,
    title: str,
    video_id: str,
) -> Path:
    """Build a filesystem path for an unmatched track.

    Unmatched tracks are OMVs where no confident ATV album match was found.
    They are stored in a flat ``_Unmatched`` folder with the video ID appended
    to guarantee uniqueness.

    Path structure: base/_Unmatched/Artist - Title [videoId]

    Args:
        base: Base directory for downloads.
        artist: Artist name from the video listing.
        title: Track title from the video listing.
        video_id: YouTube video ID (ensures filename uniqueness).

    Returns:
        Full path to the track file (without extension).

    Example:
        >>> build_unmatched_track_path(
        ...     Path("/music"), "Wiz Khalifa", "Mercury Retrograde", "-HJ0ZGkdlTk"
        ... )
        PosixPath('/music/_Unmatched/Wiz Khalifa - Mercury Retrograde [-HJ0ZGkdlTk]')
    """
    safe_artist = clean_filename(artist) or "Unknown Artist"
    safe_title = clean_filename(title) or "Unknown Track"
    track_name = f"{safe_artist} - {safe_title} [{video_id}]"

    return base / "_Unmatched" / track_name
