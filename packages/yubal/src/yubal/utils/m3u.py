"""M3U playlist file generation utilities.

M3U files are written with UTF-8 encoding, which is the modern standard
supported by most media players.
"""

import logging
from os.path import relpath
from pathlib import Path

from yubal.models.domain import TrackMetadata
from yubal.utils.cover import fetch_cover
from yubal.utils.filename import clean_filename

logger = logging.getLogger(__name__)


def generate_m3u(tracks: list[tuple[TrackMetadata, Path]], m3u_path: Path) -> str:
    """Generate M3U playlist content with paths relative to the M3U file location.

    Creates an extended M3U format file with track duration and title information.

    Args:
        tracks: List of tuples containing (TrackMetadata, file_path) for each track.
        m3u_path: Path where the M3U file will be written (used for relative paths).

    Returns:
        M3U file content as a string.

    Example:
        >>> from pathlib import Path
        >>> tracks = [(track_meta, Path("/music/Artist/2024 - Album/01 - Song.opus"))]
        >>> m3u_path = Path("/music/Playlists/My Playlist.m3u")
        >>> content = generate_m3u(tracks, m3u_path)
        >>> print(content)
        #EXTM3U
        #EXTINF:-1,Artist One; Artist Two - Song Title
        ../Artist/2024 - Album/01 - Song.opus
    """
    lines = ["#EXTM3U"]

    for track, file_path in tracks:
        # Get duration from track metadata, use -1 if unknown
        duration = track.duration_seconds if track.duration_seconds is not None else -1

        # Format: Artist - Title
        display_title = f"{track.artist} - {track.title}"

        # EXTINF line: #EXTINF:duration,display title
        lines.append(f"#EXTINF:{duration},{display_title}")

        # Relative path from M3U file location to track file
        # Note: pathlib.Path.relative_to() doesn't support going up with '..'
        # so we use os.path.relpath which handles this correctly
        try:
            relative_path = relpath(file_path, m3u_path.parent)
        except ValueError:
            # Fall back to absolute if on different drives (Windows)
            relative_path = str(file_path)
        lines.append(relative_path)

    # Ensure trailing newline
    return "\n".join(lines) + "\n"


def _format_playlist_filename(playlist_name: str, playlist_id: str) -> str:
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


def write_m3u(
    base_path: Path,
    playlist_name: str,
    playlist_id: str,
    tracks: list[tuple[TrackMetadata, Path]],
) -> Path:
    """Write an M3U playlist file to the Playlists folder.

    Creates the Playlists directory if it doesn't exist.
    Sanitizes the playlist name for safe filesystem usage.
    Appends a truncated playlist ID to avoid filename collisions.

    Args:
        base_path: Base directory for downloads (e.g., /music or ./data).
        playlist_name: Name of the playlist (will be sanitized for filename).
        playlist_id: Unique playlist ID (last 8 chars appended to filename).
        tracks: List of tuples containing (TrackMetadata, file_path) for each track.

    Returns:
        Path to the written M3U file.

    Example:
        >>> from pathlib import Path
        >>> tracks = [(track_meta, Path("/music/Artist/2024 - Album/01 - Song.opus"))]
        >>> m3u_path = write_m3u(Path("/music"), "My Favorites", "PLxyz123abc", tracks)
        >>> print(m3u_path)
        /music/Playlists/My Favorites [z123abc].m3u
    """
    # Create Playlists directory
    playlists_dir = base_path / "Playlists"
    playlists_dir.mkdir(parents=True, exist_ok=True)

    # Build M3U file path with ID suffix
    filename = _format_playlist_filename(playlist_name, playlist_id)
    m3u_path = playlists_dir / f"{filename}.m3u"

    # Generate and write content
    content = generate_m3u(tracks, m3u_path)
    m3u_path.write_text(content, encoding="utf-8")

    return m3u_path


def write_playlist_cover(
    base_path: Path,
    playlist_name: str,
    playlist_id: str,
    cover_url: str | None,
) -> Path | None:
    """Write a playlist cover image as a sidecar file.

    Creates a JPEG file with the same name as the playlist M3U file.
    Most media players (Jellyfin, Plex, foobar2000) will automatically
    pick up this sidecar image.

    Args:
        base_path: Base directory for downloads (e.g., /music or ./data).
        playlist_name: Name of the playlist (will be sanitized for filename).
        playlist_id: Unique playlist ID (last 8 chars appended to filename).
        cover_url: URL of the cover image to download.

    Returns:
        Path to the written cover file, or None if no cover URL provided
        or download failed.

    Example:
        >>> from pathlib import Path
        >>> cover_path = write_playlist_cover(
        ...     Path("/music"),
        ...     "My Favorites",
        ...     "PLxyz123abc",
        ...     "https://example.com/cover.jpg"
        ... )
        >>> print(cover_path)
        /music/Playlists/My Favorites [z123abc].jpg
    """
    if not cover_url:
        return None

    cover_data = fetch_cover(cover_url)
    if not cover_data:
        return None

    # Create Playlists directory
    playlists_dir = base_path / "Playlists"
    playlists_dir.mkdir(parents=True, exist_ok=True)

    # Build cover file path with ID suffix
    filename = _format_playlist_filename(playlist_name, playlist_id)
    cover_path = playlists_dir / f"{filename}.jpg"
    cover_path.write_bytes(cover_data)

    logger.debug("Wrote playlist cover: %s", cover_path)

    return cover_path
