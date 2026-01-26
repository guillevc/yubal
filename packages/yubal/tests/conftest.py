"""Test fixtures and configuration."""

import pytest
from yubal.models.ytmusic import (
    Album,
    AlbumRef,
    AlbumTrack,
    Artist,
    Playlist,
    PlaylistTrack,
    SearchResult,
    SongDetails,
    Thumbnail,
    VideoDetails,
)


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
def sample_search_result(sample_album_ref: AlbumRef) -> SearchResult:
    """Create a sample search result."""
    return SearchResult.model_validate(
        {
            "videoId": "search123",
            "videoType": "MUSIC_VIDEO_TYPE_ATV",
            "album": {"id": sample_album_ref.id, "name": sample_album_ref.name},
        }
    )


@pytest.fixture
def sample_video_details(sample_thumbnail: Thumbnail) -> VideoDetails:
    """Create sample video details."""
    return VideoDetails.model_validate(
        {
            "videoId": "song123",
            "title": "Test Song",
            "author": "Test Artist",
            "musicVideoType": "MUSIC_VIDEO_TYPE_ATV",
            "thumbnails": [
                {
                    "url": sample_thumbnail.url,
                    "width": sample_thumbnail.width,
                    "height": sample_thumbnail.height,
                }
            ],
        }
    )


@pytest.fixture
def sample_song_details(sample_video_details: VideoDetails) -> SongDetails:
    """Create sample song details."""
    return SongDetails.model_validate(
        {
            "videoDetails": {
                "videoId": sample_video_details.video_id,
                "title": sample_video_details.title,
                "author": sample_video_details.author,
                "musicVideoType": sample_video_details.music_video_type,
            }
        }
    )


class MockYTMusicClient:
    """Mock YouTube Music client for testing."""

    def __init__(
        self,
        playlist: Playlist | None = None,
        album: Album | None = None,
        search_results: list[SearchResult] | None = None,
        song_details: SongDetails | None = None,
    ) -> None:
        self._playlist = playlist
        self._album = album
        self._search_results = search_results or []
        self._song_details = song_details
        self.get_playlist_calls: list[str] = []
        self.get_album_calls: list[str] = []
        self.search_songs_calls: list[str] = []
        self.get_song_calls: list[str] = []

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

    def get_song(self, video_id: str) -> SongDetails:
        """Mock get_song."""
        self.get_song_calls.append(video_id)
        if self._song_details is None:
            raise ValueError("No song details configured")
        return self._song_details

    def search_songs(self, query: str) -> list[SearchResult]:
        """Mock search_songs."""
        self.search_songs_calls.append(query)
        return self._search_results


@pytest.fixture
def mock_client(
    sample_playlist: Playlist,
    sample_album: Album,
    sample_search_result: SearchResult,
    sample_song_details: SongDetails,
) -> MockYTMusicClient:
    """Create a mock client with sample data."""
    return MockYTMusicClient(
        playlist=sample_playlist,
        album=sample_album,
        search_results=[sample_search_result],
        song_details=sample_song_details,
    )
