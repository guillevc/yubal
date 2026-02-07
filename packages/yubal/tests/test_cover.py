"""Tests for cover art fetching and playlist cover writing."""

from collections.abc import Callable
from email.message import Message
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest
from yubal.models.enums import VideoType
from yubal.models.track import TrackMetadata
from yubal.utils.cover import (
    clear_cover_cache,
    fetch_cover,
    get_cover_cache_size,
    write_playlist_cover,
)
from yubal.utils.m3u import write_m3u


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


class TestWritePlaylistCover:
    """Tests for write_playlist_cover function."""

    def test_returns_none_when_no_cover_url(self, tmp_path: Path) -> None:
        """Should return None when cover_url is None."""
        result = write_playlist_cover(tmp_path, "My Playlist", "PLtest12345678", None)

        assert result is None

    def test_returns_none_when_empty_cover_url(self, tmp_path: Path) -> None:
        """Should return None when cover_url is empty string."""
        result = write_playlist_cover(tmp_path, "My Playlist", "PLtest12345678", "")

        assert result is None

    @patch("yubal.utils.cover.fetch_cover")
    def test_returns_none_when_fetch_fails(
        self, mock_fetch: MagicMock, tmp_path: Path
    ) -> None:
        """Should return None when fetch_cover returns None."""
        mock_fetch.return_value = None

        result = write_playlist_cover(
            tmp_path, "My Playlist", "PLtest12345678", "https://example.com/cover.jpg"
        )

        assert result is None
        mock_fetch.assert_called_once_with("https://example.com/cover.jpg")

    @patch("yubal.utils.cover.fetch_cover")
    def test_creates_playlists_directory(
        self, mock_fetch: MagicMock, tmp_path: Path
    ) -> None:
        """Should create Playlists directory if it doesn't exist."""
        mock_fetch.return_value = b"\xff\xd8\xff\xe0"  # JPEG magic bytes

        write_playlist_cover(
            tmp_path, "My Playlist", "PLtest12345678", "https://example.com/cover.jpg"
        )

        assert (tmp_path / "Playlists").exists()
        assert (tmp_path / "Playlists").is_dir()

    @patch("yubal.utils.cover.fetch_cover")
    def test_writes_cover_file(self, mock_fetch: MagicMock, tmp_path: Path) -> None:
        """Should write cover image as JPEG sidecar file."""
        cover_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        mock_fetch.return_value = cover_bytes

        cover_path = write_playlist_cover(
            tmp_path, "My Favorites", "PLtest12345678", "https://example.com/cover.jpg"
        )

        assert cover_path is not None
        assert cover_path.exists()
        assert cover_path.read_bytes() == cover_bytes

    @patch("yubal.utils.cover.fetch_cover")
    def test_returns_correct_path_with_id_suffix(
        self, mock_fetch: MagicMock, tmp_path: Path
    ) -> None:
        """Should return path with playlist ID suffix."""
        mock_fetch.return_value = b"\xff\xd8\xff\xe0"

        cover_path = write_playlist_cover(
            tmp_path, "My Favorites", "PLtest12345678", "https://example.com/cover.jpg"
        )

        assert cover_path == tmp_path / "Playlists" / "My Favorites [12345678].jpg"

    @patch("yubal.utils.cover.fetch_cover")
    def test_sanitizes_playlist_name(
        self, mock_fetch: MagicMock, tmp_path: Path
    ) -> None:
        """Should sanitize playlist name for safe filename."""
        mock_fetch.return_value = b"\xff\xd8\xff\xe0"

        cover_path = write_playlist_cover(
            tmp_path,
            "My/Favorites: Best<Songs>",
            "PLtest12345678",
            "https://example.com/cover.jpg",
        )

        assert cover_path is not None
        assert cover_path.exists()
        # Should not contain invalid characters (except the ID suffix brackets)
        name_without_suffix = cover_path.stem.rsplit(" [", 1)[0]
        assert "/" not in name_without_suffix
        assert ":" not in name_without_suffix
        assert "<" not in name_without_suffix
        assert ">" not in name_without_suffix

    @patch("yubal.utils.cover.fetch_cover")
    def test_handles_empty_playlist_name(
        self, mock_fetch: MagicMock, tmp_path: Path
    ) -> None:
        """Should use fallback name for empty playlist name."""
        mock_fetch.return_value = b"\xff\xd8\xff\xe0"

        cover_path = write_playlist_cover(
            tmp_path, "", "PLtest12345678", "https://example.com/cover.jpg"
        )

        assert cover_path is not None
        assert cover_path.name == "Untitled Playlist [12345678].jpg"

    @patch("yubal.utils.cover.fetch_cover")
    def test_sidecar_matches_m3u_name(
        self, mock_fetch: MagicMock, tmp_path: Path
    ) -> None:
        """Should create cover with same base name as M3U file."""
        mock_fetch.return_value = b"\xff\xd8\xff\xe0"
        sample_track = TrackMetadata(
            omv_video_id="omv123",
            atv_video_id="atv123",
            title="Airbag",
            artists=["Radiohead"],
            album="OK Computer",
            album_artists=["Radiohead"],
            track_number=1,
            total_tracks=12,
            year="1997",
            cover_url="https://example.com/cover.jpg",
            video_type=VideoType.ATV,
        )
        track_path = tmp_path / "Radiohead" / "1997 - OK Computer" / "01 - Airbag.opus"
        playlist_id = "PLtest12345678"

        m3u_path = write_m3u(
            tmp_path, "My Favorites", playlist_id, [(sample_track, track_path)]
        )
        cover_path = write_playlist_cover(
            tmp_path, "My Favorites", playlist_id, "https://example.com/cover.jpg"
        )

        assert cover_path is not None
        assert m3u_path.stem == cover_path.stem  # Same base name
        assert m3u_path.suffix == ".m3u"
        assert cover_path.suffix == ".jpg"

    @patch("yubal.utils.cover.fetch_cover")
    def test_different_ids_create_different_files(
        self, mock_fetch: MagicMock, tmp_path: Path
    ) -> None:
        """Should create separate covers for same-name playlists with different IDs."""
        mock_fetch.return_value = b"\xff\xd8\xff\xe0"

        cover_path1 = write_playlist_cover(
            tmp_path, "Favorites", "PLuser1_abc123", "https://example.com/cover1.jpg"
        )
        cover_path2 = write_playlist_cover(
            tmp_path, "Favorites", "PLuser2_xyz789", "https://example.com/cover2.jpg"
        )

        assert cover_path1 is not None
        assert cover_path2 is not None
        assert cover_path1 != cover_path2
        assert cover_path1.exists()
        assert cover_path2.exists()
        assert "abc123" in cover_path1.name
        assert "xyz789" in cover_path2.name
