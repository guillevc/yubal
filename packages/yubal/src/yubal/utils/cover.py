"""Cover art fetching with caching."""

from __future__ import annotations

import logging
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
    """

    def __init__(self) -> None:
        """Initialize an empty cover cache."""
        self._cache: dict[str, bytes] = {}

    def fetch(self, url: str | None, timeout: float = 30.0) -> bytes | None:
        """Fetch cover art from URL with caching.

        Args:
            url: Cover art URL.
            timeout: Request timeout in seconds.

        Returns:
            Cover image bytes or None if unavailable.
        """
        if not url:
            return None

        if url in self._cache:
            logger.debug("Cover cache hit: %s", url)
            return self._cache[url]

        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": f"yubal/{_VERSION}"},
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read()
                self._cache[url] = data
                logger.debug("Fetched and cached cover: %s (%d bytes)", url, len(data))
                return data
        except (HTTPError, URLError, OSError, TimeoutError) as e:
            logger.warning("Failed to fetch cover from %s: %s", url, e)
            return None

    def clear(self) -> None:
        """Clear the cover art cache."""
        self._cache.clear()

    def __len__(self) -> int:
        """Get the number of cached cover images."""
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
