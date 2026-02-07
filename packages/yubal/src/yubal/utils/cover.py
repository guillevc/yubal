"""Cover art fetching with caching."""

import logging
import threading
import urllib.request
from importlib.metadata import version
from pathlib import Path
from urllib.error import HTTPError, URLError

from yubal.utils.filename import format_playlist_filename

logger = logging.getLogger(__name__)

# Get version from package metadata for User-Agent
_VERSION = version("yubal")


class CoverCache:
    """Thread-safe cover art cache with explicit lifecycle management.

    This class provides caching for cover art downloads to avoid
    redundant network requests for the same album artwork.
    Uses threading.Lock for thread-safe concurrent access.
    """

    __slots__ = ("_cache", "_lock")

    def __init__(self) -> None:
        """Initialize an empty cover cache with thread lock."""
        self._cache: dict[str, bytes] = {}
        self._lock = threading.Lock()

    def fetch(self, url: str | None, timeout: float = 30.0) -> bytes | None:
        """Fetch cover art from URL with caching.

        Thread-safe: uses lock for cache access to prevent race conditions.

        Args:
            url: Cover art URL.
            timeout: Request timeout in seconds.

        Returns:
            Cover image bytes or None if unavailable.
        """
        if not url:
            return None

        # Check cache with lock
        with self._lock:
            if url in self._cache:
                logger.debug("Cover cache hit: %s", url)
                return self._cache[url]

        # Fetch outside lock to avoid blocking other threads
        data = self._fetch_from_network(url, timeout)

        if data:
            with self._lock:
                self._cache[url] = data

        return data

    def _fetch_from_network(self, url: str, timeout: float) -> bytes | None:
        """Fetch cover art from network.

        Args:
            url: Cover art URL.
            timeout: Request timeout in seconds.

        Returns:
            Cover image bytes or None if fetch failed.
        """
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": f"yubal/{_VERSION}"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read()
                logger.debug("Fetched cover: %s (%d bytes)", url, len(data))
                return data
        except (HTTPError, URLError, OSError, TimeoutError) as e:
            logger.warning("Failed to fetch cover from %s: %s", url, e)
            return None

    def clear(self) -> None:
        """Clear the cover art cache. Thread-safe."""
        with self._lock:
            self._cache.clear()

    def __len__(self) -> int:
        """Get the number of cached cover images. Thread-safe."""
        with self._lock:
            return len(self._cache)


# Default instance for backwards compatibility
_default_cache = CoverCache()


def fetch_cover(url: str | None, timeout: float = 30.0) -> bytes | None:
    """Fetch cover art from URL with caching.

    Args:
        url: Cover art URL.
        timeout: Request timeout in seconds.

    Returns:
        Cover image bytes or None if unavailable.
    """
    return _default_cache.fetch(url, timeout)


def clear_cover_cache() -> None:
    """Clear the cover art cache."""
    _default_cache.clear()


def get_cover_cache_size() -> int:
    """Get the number of cached cover images.

    Returns:
        Number of URLs currently cached.
    """
    return len(_default_cache)


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
    filename = format_playlist_filename(playlist_name, playlist_id)
    cover_path = playlists_dir / f"{filename}.jpg"
    cover_path.write_bytes(cover_data)

    logger.debug("Wrote playlist cover: %s", cover_path)

    return cover_path
