"""Cleanup utilities for partial downloads and temporary files."""

from pathlib import Path


def cleanup_part_files(directory: Path) -> int:
    """Remove .part files from a directory tree.

    yt-dlp creates .part files during downloads. If a download is interrupted,
    these partial files should be cleaned up to avoid leaving incomplete data.

    Args:
        directory: Base directory to search for .part files recursively.

    Returns:
        Number of .part files removed.
    """
    cleaned = 0

    try:
        for part_file in directory.rglob("*.part"):
            try:
                part_file.unlink(missing_ok=True)
                cleaned += 1
            except OSError:
                pass  # Best effort cleanup
    except OSError:
        pass  # Directory might not exist

    return cleaned
