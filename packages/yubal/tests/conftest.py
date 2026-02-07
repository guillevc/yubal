"""Test fixtures and configuration.

This module provides shared fixtures for the yubal test suite, organized into:
- Model fixtures: Sample data models for testing
- Mock fixtures: Pre-configured mocks for external dependencies
- Factory fixtures: Builders for creating customized test data
"""

from collections.abc import Callable
from unittest.mock import MagicMock

import pytest
from yubal.models.ytmusic import (
    Album,
    AlbumRef,
    AlbumTrack,
    Artist,
    Playlist,
    PlaylistTrack,
    SearchResult,
    Thumbnail,
)

# =============================================================================
# Model Fixtures - Basic building blocks
# =============================================================================


@pytest.fixture
def sample_artist() -> Artist:
    """Create a sample artist."""
    return Artist(name="Test Artist", id="artist123")


@pytest.fixture
def sample_artists() -> list[Artist]:
    """Create a list of sample artists."""
    return [
        Artist(name="Artist One", id="artist1"),
        Artist(name="Artist Two", id="artist2"),
    ]


@pytest.fixture
def sample_thumbnail() -> Thumbnail:
    """Create a sample thumbnail."""
    return Thumbnail(url="https://example.com/thumb.jpg", width=544, height=544)


@pytest.fixture
def sample_thumbnails() -> list[Thumbnail]:
    """Create a list of sample thumbnails."""
    return [
        Thumbnail(url="https://example.com/small.jpg", width=120, height=90),
        Thumbnail(url="https://example.com/medium.jpg", width=320, height=180),
        Thumbnail(url="https://example.com/square.jpg", width=544, height=544),
    ]


@pytest.fixture
def sample_album_ref() -> AlbumRef:
    """Create a sample album reference."""
    return AlbumRef(id="album123", name="Test Album")


# =============================================================================
# Composite Model Fixtures - Built from basic fixtures
# =============================================================================


@pytest.fixture
def sample_playlist_track(
    sample_artists: list[Artist],
    sample_thumbnails: list[Thumbnail],
    sample_album_ref: AlbumRef,
) -> PlaylistTrack:
    """Create a sample playlist track."""
    return PlaylistTrack.model_validate(
        {
            "videoId": "video123",
            "videoType": "MUSIC_VIDEO_TYPE_ATV",
            "title": "Test Song",
            "artists": [{"name": a.name, "id": a.id} for a in sample_artists],
            "album": {"id": sample_album_ref.id, "name": sample_album_ref.name},
            "thumbnails": [
                {"url": t.url, "width": t.width, "height": t.height}
                for t in sample_thumbnails
            ],
            "duration_seconds": 240,
        }
    )


@pytest.fixture
def sample_album_track(sample_artists: list[Artist]) -> AlbumTrack:
    """Create a sample album track."""
    return AlbumTrack.model_validate(
        {
            "videoId": "albumvideo123",
            "title": "Test Song",
            "artists": [{"name": a.name, "id": a.id} for a in sample_artists],
            "trackNumber": 5,
            "duration_seconds": 240,
        }
    )


@pytest.fixture
def sample_album(
    sample_artists: list[Artist],
    sample_thumbnails: list[Thumbnail],
    sample_album_track: AlbumTrack,
) -> Album:
    """Create a sample album."""
    return Album.model_validate(
        {
            "title": "Test Album",
            "artists": [{"name": a.name, "id": a.id} for a in sample_artists],
            "year": "2024",
            "thumbnails": [
                {"url": t.url, "width": t.width, "height": t.height}
                for t in sample_thumbnails
            ],
            "tracks": [
                {
                    "videoId": sample_album_track.video_id,
                    "title": sample_album_track.title,
                    "artists": [
                        {"name": a.name, "id": a.id} for a in sample_album_track.artists
                    ],
                    "trackNumber": sample_album_track.track_number,
                    "duration_seconds": sample_album_track.duration_seconds,
                }
            ],
        }
    )


@pytest.fixture
def sample_playlist(sample_playlist_track: PlaylistTrack) -> Playlist:
    """Create a sample playlist."""
    return Playlist.model_validate(
        {
            "title": "Test Playlist",
            "tracks": [
                {
                    "videoId": sample_playlist_track.video_id,
                    "videoType": sample_playlist_track.video_type,
                    "title": sample_playlist_track.title,
                    "artists": [
                        {"name": a.name, "id": a.id}
                        for a in sample_playlist_track.artists
                    ],
                    "album": {
                        "id": sample_playlist_track.album.id,
                        "name": sample_playlist_track.album.name,
                    }
                    if sample_playlist_track.album
                    else None,
                    "thumbnails": [
                        {"url": t.url, "width": t.width, "height": t.height}
                        for t in sample_playlist_track.thumbnails
                    ],
                    "duration_seconds": sample_playlist_track.duration_seconds,
                }
            ],
        }
    )


@pytest.fixture
def sample_search_result(
    sample_album_ref: AlbumRef, sample_artists: list[Artist]
) -> SearchResult:
    """Create a sample search result."""
    return SearchResult.model_validate(
        {
            "videoId": "search123",
            "videoType": "MUSIC_VIDEO_TYPE_ATV",
            "title": "Test Song",
            "artists": [{"name": a.name, "id": a.id} for a in sample_artists],
            "album": {"id": sample_album_ref.id, "name": sample_album_ref.name},
        }
    )


# =============================================================================
# Factory Fixtures - For creating customized test data
# =============================================================================


@pytest.fixture
def make_artist() -> Callable[..., Artist]:
    """Factory fixture for creating artists with custom attributes."""

    def _make_artist(
        name: str = "Test Artist",
        id: str | None = "artist123",
    ) -> Artist:
        return Artist(name=name, id=id)

    return _make_artist


@pytest.fixture
def make_thumbnail() -> Callable[..., Thumbnail]:
    """Factory fixture for creating thumbnails with custom dimensions."""

    def _make_thumbnail(
        url: str = "https://example.com/thumb.jpg",
        width: int = 544,
        height: int = 544,
    ) -> Thumbnail:
        return Thumbnail(url=url, width=width, height=height)

    return _make_thumbnail


@pytest.fixture
def make_album_track() -> Callable[..., AlbumTrack]:
    """Factory fixture for creating album tracks with custom attributes."""

    def _make_album_track(
        video_id: str = "video123",
        title: str = "Test Song",
        artists: list[dict] | None = None,
        track_number: int = 1,
        duration_seconds: int = 240,
    ) -> AlbumTrack:
        if artists is None:
            artists = [{"name": "Test Artist", "id": "artist1"}]
        return AlbumTrack.model_validate(
            {
                "videoId": video_id,
                "title": title,
                "artists": artists,
                "trackNumber": track_number,
                "duration_seconds": duration_seconds,
            }
        )

    return _make_album_track


# =============================================================================
# Mock Fixtures - For external dependencies
# =============================================================================


class MockYTMusicClient:
    """Mock YouTube Music client for testing.

    This mock tracks all API calls made during tests and returns
    pre-configured responses.
    """

    def __init__(
        self,
        playlist: Playlist | None = None,
        album: Album | None = None,
        search_results: list[SearchResult] | None = None,
    ) -> None:
        self._playlist = playlist
        self._album = album
        self._search_results = search_results or []
        self.get_playlist_calls: list[str] = []
        self.get_album_calls: list[str] = []
        self.search_songs_calls: list[str] = []

    def get_playlist(self, playlist_id: str) -> Playlist:
        """Mock get_playlist."""
        self.get_playlist_calls.append(playlist_id)
        if self._playlist is None:
            raise ValueError("No playlist configured")
        return self._playlist

    def get_album(self, album_id: str) -> Album:
        """Mock get_album."""
        self.get_album_calls.append(album_id)
        if self._album is None:
            raise ValueError("No album configured")
        return self._album

    def search_songs(self, query: str) -> list[SearchResult]:
        """Mock search_songs."""
        self.search_songs_calls.append(query)
        return self._search_results

    def get_track(self, video_id: str) -> PlaylistTrack:
        """Mock get_track - not implemented for playlist tests."""
        raise NotImplementedError("MockYTMusicClient doesn't support get_track")


@pytest.fixture
def mock_client(
    sample_playlist: Playlist,
    sample_album: Album,
    sample_search_result: SearchResult,
) -> MockYTMusicClient:
    """Create a mock client with sample data."""
    return MockYTMusicClient(
        playlist=sample_playlist,
        album=sample_album,
        search_results=[sample_search_result],
    )


@pytest.fixture
def mock_urlopen_response() -> Callable[..., MagicMock]:
    """Factory for creating mock urlopen responses.

    Usage:
        def test_example(mock_urlopen_response):
            mock_resp = mock_urlopen_response(b"response data")
            with patch("urllib.request.urlopen", return_value=mock_resp):
                ...
    """

    def _create_response(data: bytes = b"mock data") -> MagicMock:
        mock_response = MagicMock()
        mock_response.read.return_value = data
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        return mock_response

    return _create_response
