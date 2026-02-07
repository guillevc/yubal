"""Tests for cover art fetching."""

from collections.abc import Callable
from email.message import Message
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest
from yubal.utils.cover import clear_cover_cache, fetch_cover, get_cover_cache_size


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Clear cover cache before each test."""
    clear_cover_cache()


class TestFetchCover:
    """Tests for fetch_cover function."""

    @pytest.mark.parametrize("url", [None, ""])
    def test_returns_none_for_invalid_url(self, url: str | None) -> None:
        """Should return None when URL is None or empty."""
        assert fetch_cover(url) is None

    def test_fetches_cover_successfully(
        self, mock_urlopen_response: Callable[..., MagicMock]
    ) -> None:
        """Should fetch and return cover bytes."""
        mock_resp = mock_urlopen_response(b"fake image data")
        with patch("yubal.utils.cover.urllib.request.urlopen", return_value=mock_resp):
            result = fetch_cover("https://example.com/cover.jpg")
        assert result == b"fake image data"

    def test_caches_cover(
        self, mock_urlopen_response: Callable[..., MagicMock]
    ) -> None:
        """Should cache fetched cover and return from cache on second call."""
        mock_resp = mock_urlopen_response(b"cached image")
        with patch(
            "yubal.utils.cover.urllib.request.urlopen", return_value=mock_resp
        ) as mock_urlopen:
            result1 = fetch_cover("https://example.com/cover.jpg")
            result2 = fetch_cover("https://example.com/cover.jpg")

        assert result1 == result2 == b"cached image"
        assert mock_urlopen.call_count == 1

    def test_different_urls_not_cached_together(
        self, mock_urlopen_response: Callable[..., MagicMock]
    ) -> None:
        """Should cache different URLs separately."""
        mock_resp1 = mock_urlopen_response(b"image 1")
        mock_resp2 = mock_urlopen_response(b"image 2")

        with patch("yubal.utils.cover.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = [mock_resp1, mock_resp2]
            result1 = fetch_cover("https://example.com/cover1.jpg")
            result2 = fetch_cover("https://example.com/cover2.jpg")

        assert result1 == b"image 1"
        assert result2 == b"image 2"
        assert mock_urlopen.call_count == 2

    @pytest.mark.parametrize(
        "error",
        [
            HTTPError(
                "https://example.com/cover.jpg", 404, "Not Found", Message(), None
            ),
            URLError("Connection refused"),
            TimeoutError("Connection timed out"),
        ],
        ids=["http_error", "url_error", "timeout"],
    )
    def test_handles_network_errors(self, error: Exception) -> None:
        """Should return None on network errors."""
        with patch("yubal.utils.cover.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = error
            result = fetch_cover("https://example.com/cover.jpg")
        assert result is None


class TestClearCoverCache:
    """Tests for clear_cover_cache function."""

    def test_clears_cache(
        self, mock_urlopen_response: Callable[..., MagicMock]
    ) -> None:
        """Should clear all cached covers."""
        mock_resp = mock_urlopen_response(b"image")
        with patch("yubal.utils.cover.urllib.request.urlopen", return_value=mock_resp):
            fetch_cover("https://example.com/cover.jpg")
            assert get_cover_cache_size() == 1
            clear_cover_cache()
            assert get_cover_cache_size() == 0


class TestGetCoverCacheSize:
    """Tests for get_cover_cache_size function."""

    def test_returns_zero_when_empty(self) -> None:
        """Should return 0 for empty cache."""
        assert get_cover_cache_size() == 0

    def test_returns_correct_count(
        self, mock_urlopen_response: Callable[..., MagicMock]
    ) -> None:
        """Should return correct number of cached items."""
        mock_resp = mock_urlopen_response(b"image")
        with patch("yubal.utils.cover.urllib.request.urlopen", return_value=mock_resp):
            fetch_cover("https://example.com/cover1.jpg")
            assert get_cover_cache_size() == 1
            fetch_cover("https://example.com/cover2.jpg")
            assert get_cover_cache_size() == 2
