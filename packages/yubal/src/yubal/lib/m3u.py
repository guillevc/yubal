"""M3U playlist file generation utilities.

M3U files are written with UTF-8 encoding, which is the modern standard
supported by most media players.
"""

import logging
from os.path import relpath
from pathlib import Path

from yubal.models.track import TrackMetadata
from yubal.utils.filename import format_playlist_filename

logger = logging.getLogger(__name__)


def generate_m3u(
    tracks: list[tuple[TrackMetadata, Path]],
    m3u_path: Path,
    playlist_name: str,
) -> str:
    """Generate M3U playlist content with paths relative to the M3U file location.

    Creates an extended M3U format file with track duration and title information.
    Emits a ``#PLAYLIST:`` directive so players (Navidrome, VLC, Plex, MPD, etc.)
    display the playlist by its name rather than by the on-disk filename, which
    includes a collision-avoiding ID suffix.

    Args:
        tracks: List of tuples containing (TrackMetadata, file_path) for each track.
        m3u_path: Path where the M3U file will be written (used for relative paths).
        playlist_name: Human-readable playlist name (used for ``#PLAYLIST:``).

    Returns:
        M3U file content as a string.

    Example:
        >>> from pathlib import Path
        >>> tracks = [(track_meta, Path("/music/Artist/2024 - Album/01 - Song.opus"))]
        >>> m3u_path = Path("/music/Playlists/My Playlist.m3u")
        >>> content = generate_m3u(tracks, m3u_path, "My Playlist")
        >>> print(content)
        #EXTM3U
        #PLAYLIST:My Playlist
        #EXTINF:-1,Artist One; Artist Two - Song Title
        ../Artist/2024 - Album/01 - Song.opus
    """
    lines = ["#EXTM3U", f"#PLAYLIST:{playlist_name}"]

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


def write_m3u(
    base_path: Path,
    playlist_name: str,
    playlist_id: str,
    tracks: list[tuple[TrackMetadata, Path]],
    *,
    ascii_filenames: bool = False,
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
        ascii_filenames: If True, transliterate unicode to ASCII in filenames.

    Returns:
        Path to the written M3U file.

    Example:
        >>> from pathlib import Path
        >>> tracks = [(track_meta, Path("/music/Artist/2024 - Album/01 - Song.opus"))]
        >>> m3u_path = write_m3u(Path("/music"), "My Favorites", "PLxyz123abc", tracks)
        >>> print(m3u_path)
        /music/_Playlists/My Favorites [z123abc].m3u
    """
    # Create _Playlists directory
    playlists_dir = base_path / "_Playlists"
    playlists_dir.mkdir(parents=True, exist_ok=True)

    # Build M3U file path with ID suffix
    filename = format_playlist_filename(
        playlist_name, playlist_id, ascii_filenames=ascii_filenames
    )
    m3u_path = playlists_dir / f"{filename}.m3u"

    # Generate and write content
    content = generate_m3u(tracks, m3u_path, playlist_name)
    m3u_path.write_text(content, encoding="utf-8")

    return m3u_path
