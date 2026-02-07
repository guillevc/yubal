"""Utility functions for yubal.

Available via `from yubal.utils import ...` for power users.
Not re-exported at the top-level `yubal` package.
"""

from yubal.utils.artists import format_artists
from yubal.utils.cleanup import cleanup_part_files
from yubal.utils.cookies import cookies_to_ytmusic_auth, is_authenticated_cookies
from yubal.utils.cover import (
    clear_cover_cache,
    fetch_cover,
    get_cover_cache_size,
    write_playlist_cover,
)
from yubal.utils.filename import (
    build_track_path,
    clean_filename,
    format_playlist_filename,
)
from yubal.utils.m3u import generate_m3u, write_m3u
from yubal.utils.thumbnails import get_square_thumbnail
from yubal.utils.url import is_single_track_url, parse_playlist_id, parse_video_id

__all__ = [
    "build_track_path",
    "clean_filename",
    "cleanup_part_files",
    "clear_cover_cache",
    "cookies_to_ytmusic_auth",
    "fetch_cover",
    "format_artists",
    "format_playlist_filename",
    "generate_m3u",
    "get_cover_cache_size",
    "get_square_thumbnail",
    "is_authenticated_cookies",
    "is_single_track_url",
    "parse_playlist_id",
    "parse_video_id",
    "write_m3u",
    "write_playlist_cover",
]
