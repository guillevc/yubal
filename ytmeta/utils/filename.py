"""Filename sanitization utilities for safe filesystem paths."""

from pathlib import Path

from pathvalidate import sanitize_filename
from unidecode import unidecode


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
    return sanitize_filename(unidecode(s))


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
