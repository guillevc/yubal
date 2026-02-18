"""Filename sanitization utilities for safe filesystem paths."""

from pathlib import Path

from pathvalidate import sanitize_filename
from unidecode import unidecode


def clean_filename(s: str, *, ascii_filenames: bool = False) -> str:
    """Sanitize a string for use in a filename.

    Optionally transliterates unicode characters to ASCII equivalents,
    then removes or replaces characters that are invalid in filenames.

    Args:
        s: String to sanitize.
        ascii_filenames: If True, transliterate unicode to ASCII before sanitizing.

    Returns:
        Sanitized string safe for use in filenames.

    Example:
        >>> clean_filename("Bjork - Joga")
        'Bjork - Joga'
        >>> clean_filename("AC/DC")
        'ACDC'
        >>> clean_filename("Björk", ascii_filenames=True)
        'Bjork'
    """
    if ascii_filenames:
        s = unidecode(s)
    return sanitize_filename(s)


def format_playlist_filename(
    playlist_name: str, playlist_id: str, *, ascii_filenames: bool = False
) -> str:
    """Format playlist filename with ID suffix to avoid collisions.

    Args:
        playlist_name: Name of the playlist (will be sanitized).
        playlist_id: Unique playlist ID (last 8 chars used as suffix).
        ascii_filenames: If True, transliterate unicode to ASCII.

    Returns:
        Formatted filename without extension, e.g., "My Favorites [abcd1234]".
    """
    safe_name = clean_filename(playlist_name, ascii_filenames=ascii_filenames)
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
    *,
    ascii_filenames: bool = False,
) -> Path:
    """Build a filesystem path for a track following the convention.

    Creates a path structure: base/Artist/YEAR - Album/NN - Title
    When year is unknown: base/Artist/Album/NN - Title

    Args:
        base: Base directory for downloads.
        artist: Album artist name.
        year: Release year (or None for unknown).
        album: Album name.
        track_number: Track number (or None for unknown).
        title: Track title.
        ascii_filenames: If True, transliterate unicode to ASCII.

    Returns:
        Full path to the track file (without extension).

    Example:
        >>> build_track_path(Path("/music"), "Artist", "2024", "Album", 1, "Song")
        PosixPath('/music/Artist/2024 - Album/01 - Song')
    """
    # Sanitize components
    safe_artist = (
        clean_filename(artist, ascii_filenames=ascii_filenames) or "Unknown Artist"
    )
    safe_album = (
        clean_filename(album, ascii_filenames=ascii_filenames) or "Unknown Album"
    )
    safe_title = (
        clean_filename(title, ascii_filenames=ascii_filenames) or "Unknown Track"
    )

    # Build album folder name
    album_folder = f"{year} - {safe_album}" if year else safe_album

    # Build track filename
    if track_number is not None:
        track_name = f"{track_number:02d} - {safe_title}"
    else:
        track_name = safe_title

    return base / safe_artist / album_folder / track_name


def _build_flat_track_path(
    base: Path,
    folder: str,
    artist: str,
    title: str,
    video_id: str,
    *,
    ascii_filenames: bool = False,
) -> Path:
    """Build path: base/folder/Artist - Title [videoId].

    Shared implementation for unmatched and unofficial track paths.

    Args:
        base: Base directory for downloads.
        folder: Subfolder name (e.g., "_Unmatched", "_Unofficial").
        artist: Artist name from the video listing.
        title: Track title from the video listing.
        video_id: YouTube video ID (ensures filename uniqueness).
        ascii_filenames: If True, transliterate unicode to ASCII.

    Returns:
        Full path to the track file (without extension).
    """
    safe_artist = (
        clean_filename(artist, ascii_filenames=ascii_filenames) or "Unknown Artist"
    )
    safe_title = (
        clean_filename(title, ascii_filenames=ascii_filenames) or "Unknown Track"
    )
    track_name = f"{safe_artist} - {safe_title} [{video_id}]"

    return base / folder / track_name


def build_unmatched_track_path(
    base: Path,
    artist: str,
    title: str,
    video_id: str,
    *,
    ascii_filenames: bool = False,
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
        ascii_filenames: If True, transliterate unicode to ASCII.

    Returns:
        Full path to the track file (without extension).

    Example:
        >>> build_unmatched_track_path(
        ...     Path("/music"), "Wiz Khalifa", "Mercury Retrograde", "-HJ0ZGkdlTk"
        ... )
        PosixPath('/music/_Unmatched/Wiz Khalifa - Mercury Retrograde [-HJ0ZGkdlTk]')
    """
    return _build_flat_track_path(
        base, "_Unmatched", artist, title, video_id, ascii_filenames=ascii_filenames
    )


def build_unofficial_track_path(
    base: Path,
    artist: str,
    title: str,
    video_id: str,
    *,
    ascii_filenames: bool = False,
) -> Path:
    """Build a filesystem path for an unofficial (UGC) track.

    UGC tracks have unreliable metadata and are stored in a flat
    ``_Unofficial`` folder with the video ID appended for uniqueness.

    Path structure: base/_Unofficial/Artist - Title [videoId]

    Args:
        base: Base directory for downloads.
        artist: Artist name from the video listing.
        title: Track title from the video listing.
        video_id: YouTube video ID (ensures filename uniqueness).
        ascii_filenames: If True, transliterate unicode to ASCII.

    Returns:
        Full path to the track file (without extension).

    Example:
        >>> build_unofficial_track_path(
        ...     Path("/music"), "Some User", "Cool Song", "abc123"
        ... )
        PosixPath('/music/_Unofficial/Some User - Cool Song [abc123]')
    """
    return _build_flat_track_path(
        base, "_Unofficial", artist, title, video_id, ascii_filenames=ascii_filenames
    )
