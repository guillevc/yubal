"""M3U playlist file generator.

Creates M3U playlist files with relative paths for easy playback
in music players.
"""

from collections.abc import Sequence
from pathlib import Path

from loguru import logger

from yubal.services.metadata_enricher import TrackMetadata

# Translation table to remove invalid filename characters
_INVALID_CHARS = '<>:"/\\|?*'
_SANITIZE_TABLE = str.maketrans("", "", _INVALID_CHARS)


def sanitize_filename(name: str) -> str:
    """Remove invalid filename characters and prevent path traversal.

    Args:
        name: Raw string to sanitize

    Returns:
        Safe filename string, or "untitled" if result would be empty
    """
    # Remove path separators and invalid chars (str.translate is faster than loop)
    name = name.translate(_SANITIZE_TABLE)

    # Remove any remaining dots at start (prevent hidden files and ..)
    name = name.lstrip(".")

    # Final cleanup
    result = name.strip()[:100]

    # Fallback for empty result
    return result or "untitled"


def generate_m3u(
    playlist_name: str,
    track_files: Sequence[Path],
    track_metadata: Sequence[TrackMetadata],
    output_dir: Path,
) -> Path:
    """Generate M3U playlist file.

    Args:
        playlist_name: Name for the playlist (used as filename)
        track_files: Ordered list of track file paths
        track_metadata: Corresponding track metadata for EXTINF
        output_dir: Directory to write the M3U file

    Returns:
        Path to the generated M3U file
    """
    safe_name = sanitize_filename(playlist_name)
    m3u_path = output_dir / f"{safe_name}.m3u"

    lines = [
        "#EXTM3U",
        f"#PLAYLIST:{playlist_name}",
    ]

    if len(track_files) != len(track_metadata):
        logger.warning(
            "File count ({}) doesn't match metadata count ({}). "
            "Generating M3U with {} tracks.",
            len(track_files),
            len(track_metadata),
            min(len(track_files), len(track_metadata)),
        )

    for track_file, metadata in zip(track_files, track_metadata, strict=False):
        # EXTINF format: #EXTINF:duration,artist - title (duration -1 = unknown)
        lines.extend((
            f"#EXTINF:-1,{metadata.artist} - {metadata.title}",
            track_file.name,
        ))

    m3u_content = "\n".join(lines) + "\n"
    m3u_path.write_text(m3u_content, encoding="utf-8")

    logger.info("Generated M3U playlist: {}", m3u_path)
    return m3u_path
