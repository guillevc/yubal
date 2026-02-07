"""Cover art fetching with caching."""

import logging
import threading
import urllib.request
from importlib.metadata import version
from urllib.error import HTTPError, URLError

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
