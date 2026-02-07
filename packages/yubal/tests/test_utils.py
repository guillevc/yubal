"""Tests for utility functions."""

import pytest
from yubal.exceptions import PlaylistParseError
from yubal.utils import (
    is_single_track_url,
    parse_playlist_id,
    parse_video_id,
)


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


class TestIsSingleTrackUrl:
    """Tests for is_single_track_url function."""

    def test_returns_true_for_track_url(self) -> None:
        """Should return True for track URLs."""
        url = "https://music.youtube.com/watch?v=Vgpv5PtWsn4"
        assert is_single_track_url(url) is True

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
