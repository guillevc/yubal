"""Tests for utility functions."""

import pytest
from yubal.exceptions import PlaylistParseError
from yubal.utils import (
    is_single_track_url,
    parse_playlist_id,
    parse_video_id,
)
from yubal.utils.url import is_supported_url


class TestParseVideoId:
    """Tests for parse_video_id function."""

    def test_extracts_from_music_youtube_url(self) -> None:
        """Should extract video ID from YouTube Music URL."""
        url = "https://music.youtube.com/watch?v=Vgpv5PtWsn4"
        assert parse_video_id(url) == "Vgpv5PtWsn4"

    def test_extracts_from_youtube_url(self) -> None:
        """Should extract video ID from standard YouTube URL."""
        url = "https://www.youtube.com/watch?v=GkTWxDB21cA"
        assert parse_video_id(url) == "GkTWxDB21cA"

    def test_extracts_from_mobile_youtube_url(self) -> None:
        """Should extract video ID from mobile YouTube URL."""
        url = "https://m.youtube.com/watch?v=dQw4w9WgXcQ"
        assert parse_video_id(url) == "dQw4w9WgXcQ"

    def test_extracts_from_url_with_extra_params(self) -> None:
        """Should extract video ID when URL has extra parameters."""
        url = "https://music.youtube.com/watch?v=abc123&si=xyz789"
        assert parse_video_id(url) == "abc123"

    def test_returns_none_for_playlist_url(self) -> None:
        """Should return None for playlist-only URLs."""
        url = "https://music.youtube.com/playlist?list=PLtest123"
        assert parse_video_id(url) is None

    def test_returns_none_for_url_with_list_and_v(self) -> None:
        """Should return None when URL has both list and v (playlist priority)."""
        url = "https://music.youtube.com/watch?v=abc123&list=PLtest123"
        assert parse_video_id(url) is None

    def test_returns_none_for_empty_url(self) -> None:
        """Should return None for empty URLs."""
        assert parse_video_id("") is None

    def test_returns_none_for_malformed_v_param(self) -> None:
        """Should return None when v param is empty."""
        url = "https://music.youtube.com/watch?v="
        assert parse_video_id(url) is None

    def test_returns_none_for_very_long_url(self) -> None:
        """Should return None for URLs exceeding max length."""
        url = "https://music.youtube.com/watch?v=abc123&" + "x" * 2100
        assert parse_video_id(url) is None

    # --- youtu.be short URLs ---

    def test_extracts_from_youtu_be(self) -> None:
        """Should extract video ID from youtu.be short URL."""
        assert parse_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extracts_from_youtu_be_with_params(self) -> None:
        """Should extract video ID from youtu.be with tracking params."""
        assert parse_video_id("https://youtu.be/dQw4w9WgXcQ?si=abc") == "dQw4w9WgXcQ"

    def test_returns_none_for_youtu_be_with_list(self) -> None:
        """Should return None for youtu.be with playlist parameter."""
        assert parse_video_id("https://youtu.be/abc?list=PLtest") is None

    def test_extracts_from_youtu_be_http(self) -> None:
        """Should extract video ID from http youtu.be."""
        assert parse_video_id("http://youtu.be/abc123") == "abc123"

    # --- Path-based URLs (shorts, live, embed) ---

    def test_extracts_from_shorts_url(self) -> None:
        """Should extract video ID from YouTube Shorts URL."""
        assert parse_video_id("https://youtube.com/shorts/abc123") == "abc123"

    def test_extracts_from_www_shorts_url(self) -> None:
        """Should extract from www.youtube.com/shorts/."""
        assert parse_video_id("https://www.youtube.com/shorts/abc123") == "abc123"

    def test_extracts_from_mobile_shorts_url(self) -> None:
        """Should extract from m.youtube.com/shorts/."""
        assert parse_video_id("https://m.youtube.com/shorts/abc123") == "abc123"

    def test_extracts_from_live_url(self) -> None:
        """Should extract video ID from YouTube live URL."""
        assert parse_video_id("https://youtube.com/live/abc123") == "abc123"

    def test_extracts_from_embed_url(self) -> None:
        """Should extract video ID from YouTube embed URL."""
        assert parse_video_id("https://youtube.com/embed/abc123") == "abc123"

    def test_extracts_from_nocookie_embed_url(self) -> None:
        """Should extract from youtube-nocookie.com embed URL."""
        assert parse_video_id("https://youtube-nocookie.com/embed/abc123") == "abc123"

    def test_extracts_from_www_nocookie_embed_url(self) -> None:
        """Should extract from www.youtube-nocookie.com embed URL."""
        assert (
            parse_video_id("https://www.youtube-nocookie.com/embed/abc123") == "abc123"
        )

    def test_extracts_from_legacy_v_path(self) -> None:
        """Should extract video ID from legacy /v/ path."""
        assert parse_video_id("https://youtube.com/v/abc123") == "abc123"

    def test_extracts_from_legacy_e_path(self) -> None:
        """Should extract video ID from legacy /e/ path."""
        assert parse_video_id("https://youtube.com/e/abc123") == "abc123"

    def test_extracts_from_legacy_vi_path(self) -> None:
        """Should extract video ID from legacy /vi/ path."""
        assert parse_video_id("https://youtube.com/vi/abc123") == "abc123"

    def test_returns_none_for_unknown_host(self) -> None:
        """Should return None for path-based URL on unknown host."""
        assert parse_video_id("https://example.com/shorts/abc123") is None


class TestIsSingleTrackUrl:
    """Tests for is_single_track_url function."""

    def test_returns_true_for_track_url(self) -> None:
        """Should return True for track URLs."""
        url = "https://music.youtube.com/watch?v=Vgpv5PtWsn4"
        assert is_single_track_url(url) is True

    def test_returns_true_for_youtu_be(self) -> None:
        """Should return True for youtu.be short URLs."""
        assert is_single_track_url("https://youtu.be/abc123") is True

    def test_returns_true_for_shorts(self) -> None:
        """Should return True for YouTube Shorts URLs."""
        assert is_single_track_url("https://youtube.com/shorts/abc123") is True

    def test_returns_false_for_playlist_url(self) -> None:
        """Should return False for playlist URLs."""
        url = "https://music.youtube.com/playlist?list=PLtest123"
        assert is_single_track_url(url) is False

    def test_returns_false_for_url_with_both(self) -> None:
        """Should return False when URL has both v and list."""
        url = "https://music.youtube.com/watch?v=abc123&list=PLtest123"
        assert is_single_track_url(url) is False

    def test_returns_false_for_empty_url(self) -> None:
        """Should return False for empty URL."""
        assert is_single_track_url("") is False


class TestParsePlaylistId:
    """Tests for parse_playlist_id function."""

    def test_extracts_from_full_url(self) -> None:
        """Should extract playlist ID from a full URL."""
        url = "https://music.youtube.com/playlist?list=PLtest123"
        assert parse_playlist_id(url) == "PLtest123"

    def test_extracts_from_mobile_url(self) -> None:
        """Should extract playlist ID from mobile YouTube URL."""
        url = "https://m.youtube.com/playlist?list=PLtest123"
        assert parse_playlist_id(url) == "PLtest123"

    def test_extracts_from_url_with_extra_params(self) -> None:
        """Should extract playlist ID when URL has extra parameters."""
        url = "https://music.youtube.com/playlist?list=PLtest123&si=abc123"
        assert parse_playlist_id(url) == "PLtest123"

    def test_extracts_from_url_with_special_chars(self) -> None:
        """Should handle playlist IDs with underscores and hyphens."""
        url = "https://music.youtube.com/playlist?list=PL_test-123_abc"
        assert parse_playlist_id(url) == "PL_test-123_abc"

    def test_raises_for_invalid_url(self) -> None:
        """Should raise PlaylistParseError for URLs without playlist ID."""
        with pytest.raises(PlaylistParseError, match="Could not extract"):
            parse_playlist_id("https://youtube.com/watch?v=abc123")

    def test_raises_for_empty_url(self) -> None:
        """Should raise PlaylistParseError for empty URLs."""
        with pytest.raises(PlaylistParseError, match="Could not extract"):
            parse_playlist_id("")

    def test_raises_for_malformed_list_param(self) -> None:
        """Should raise PlaylistParseError when list param is empty."""
        with pytest.raises(PlaylistParseError, match="Could not extract"):
            parse_playlist_id("https://music.youtube.com/playlist?list=")

    def test_raises_for_very_long_url(self) -> None:
        """Should raise PlaylistParseError for URLs exceeding max length."""
        url = "https://music.youtube.com/playlist?list=PLtest123&" + "x" * 2100
        with pytest.raises(PlaylistParseError, match="Could not extract"):
            parse_playlist_id(url)


class TestIsSupportedUrl:
    """Tests for is_supported_url function."""

    @pytest.mark.parametrize(
        "url",
        [
            # Standard watch URLs
            "https://music.youtube.com/watch?v=abc123",
            "https://www.youtube.com/watch?v=abc123",
            "https://youtube.com/watch?v=abc123",
            "https://m.youtube.com/watch?v=abc123",
            # Playlist URLs
            "https://music.youtube.com/playlist?list=PLtest",
            "https://www.youtube.com/playlist?list=PLtest",
            "https://m.youtube.com/playlist?list=PLtest",
            # Browse URLs
            "https://music.youtube.com/browse/MPREb_test",
            # youtu.be short URLs
            "https://youtu.be/abc123",
            "http://youtu.be/abc123",
            # Shorts, live, embed
            "https://youtube.com/shorts/abc123",
            "https://m.youtube.com/shorts/abc123",
            "https://youtube.com/live/abc123",
            "https://youtube.com/embed/abc123",
            "https://youtube-nocookie.com/embed/abc123",
            "https://www.youtube-nocookie.com/embed/abc123",
            # Legacy paths
            "https://youtube.com/v/abc123",
            "https://youtube.com/e/abc123",
            "https://youtube.com/vi/abc123",
        ],
    )
    def test_accepts_supported_urls(self, url: str) -> None:
        """Should accept all supported URL formats."""
        assert is_supported_url(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "",
            "https://example.com/test",
            "https://music.youtube.com/",
            "https://music.youtube.com/watch",
            "https://youtube.com/",
            "https://youtube.com/channel/abc",
            "https://youtube.com/browse/VLPLxyz",
            "not a url",
        ],
    )
    def test_rejects_unsupported_urls(self, url: str) -> None:
        """Should reject unsupported URL formats."""
        assert is_supported_url(url) is False
