"""Tests for utility functions."""

import pytest
from yubal.exceptions import PlaylistParseError
from yubal.models.ytmusic import Artist, Thumbnail
from yubal.utils import format_artists, get_square_thumbnail, parse_playlist_id


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


class TestFormatArtists:
    """Tests for format_artists function."""

    def test_single_artist(self) -> None:
        """Should format a single artist correctly."""
        artists = [Artist(name="Taylor Swift", id="123")]
        assert format_artists(artists) == "Taylor Swift"

    def test_multiple_artists(self) -> None:
        """Should join multiple artists with semicolons."""
        artists = [
            Artist(name="John Lennon", id="1"),
            Artist(name="Paul McCartney", id="2"),
        ]
        assert format_artists(artists) == "John Lennon; Paul McCartney"

    def test_empty_list(self) -> None:
        """Should return empty string for empty list."""
        assert format_artists([]) == ""

    def test_artist_without_id(self) -> None:
        """Should handle artists without ID."""
        artists = [Artist(name="Unknown Artist", id=None)]
        assert format_artists(artists) == "Unknown Artist"

    def test_filters_empty_names(self) -> None:
        """Should skip artists with empty names."""
        artists = [
            Artist(name="Valid Artist", id="1"),
            Artist(name="", id="2"),
        ]
        assert format_artists(artists) == "Valid Artist"


class TestGetSquareThumbnail:
    """Tests for get_square_thumbnail function."""

    def test_returns_largest_square(self) -> None:
        """Should return the largest square thumbnail."""
        thumbnails = [
            Thumbnail(url="https://small.jpg", width=120, height=120),
            Thumbnail(url="https://large.jpg", width=544, height=544),
            Thumbnail(url="https://medium.jpg", width=320, height=320),
        ]
        assert get_square_thumbnail(thumbnails) == "https://large.jpg"

    def test_prefers_square_over_rectangular(self) -> None:
        """Should prefer square thumbnails over larger rectangular ones."""
        thumbnails = [
            Thumbnail(url="https://rect.jpg", width=1280, height=720),
            Thumbnail(url="https://square.jpg", width=544, height=544),
        ]
        assert get_square_thumbnail(thumbnails) == "https://square.jpg"

    def test_falls_back_to_last_thumbnail(self) -> None:
        """Should return last thumbnail if no square ones exist."""
        thumbnails = [
            Thumbnail(url="https://small.jpg", width=120, height=90),
            Thumbnail(url="https://large.jpg", width=1280, height=720),
        ]
        assert get_square_thumbnail(thumbnails) == "https://large.jpg"

    def test_returns_none_for_empty_list(self) -> None:
        """Should return None for empty list."""
        assert get_square_thumbnail([]) is None

    def test_single_square_thumbnail(self) -> None:
        """Should work with a single square thumbnail."""
        thumbnails = [Thumbnail(url="https://only.jpg", width=544, height=544)]
        assert get_square_thumbnail(thumbnails) == "https://only.jpg"
