"""Tests for MetadataExtractorService.extract_track() method."""

import pytest
from yubal.exceptions import TrackParseError
from yubal.models.enums import ContentKind, VideoType
from yubal.models.ytmusic import Album, Playlist, PlaylistTrack, SearchResult
from yubal.services.extractor import MetadataExtractorService


class MockClientForTrack:
    """Mock client for single track tests."""

    def __init__(
        self,
        track: PlaylistTrack | None = None,
        album: Album | None = None,
    ) -> None:
        self._track = track
        self._album = album
        self.get_track_calls: list[str] = []
        self.get_album_calls: list[str] = []
        self.search_songs_calls: list[str] = []

    def get_track(self, video_id: str) -> PlaylistTrack:
        self.get_track_calls.append(video_id)
        if self._track is None:
            raise ValueError("No track configured")
        return self._track

    def get_album(self, album_id: str) -> Album:
        self.get_album_calls.append(album_id)
        if self._album is None:
            raise ValueError("No album configured")
        return self._album

    def search_songs(self, query: str) -> list[SearchResult]:
        self.search_songs_calls.append(query)
        return []

    def get_playlist(self, playlist_id: str) -> Playlist:
        raise NotImplementedError("MockClientForTrack doesn't support playlists")


@pytest.fixture
def atv_track() -> PlaylistTrack:
    """ATV track with album info."""
    return PlaylistTrack.model_validate(
        {
            "videoId": "Vgpv5PtWsn4",
            "videoType": "MUSIC_VIDEO_TYPE_ATV",
            "title": "A COLD PLAY",
            "artists": [{"name": "The Kid LAROI", "id": "UC123"}],
            "album": {"id": "MPREb_123", "name": "A COLD PLAY"},
            "thumbnails": [
                {"url": "https://example.com/thumb.jpg", "width": 544, "height": 544}
            ],
            "duration_seconds": 180,
        }
    )


@pytest.fixture
def sample_album() -> Album:
    """Album with matching track."""
    return Album.model_validate(
        {
            "title": "A COLD PLAY",
            "artists": [{"name": "The Kid LAROI", "id": "UC123"}],
            "year": "2025",
            "thumbnails": [
                {"url": "https://example.com/album.jpg", "width": 544, "height": 544}
            ],
            "tracks": [
                {
                    "videoId": "Vgpv5PtWsn4",
                    "title": "A COLD PLAY",
                    "artists": [{"name": "The Kid LAROI", "id": "UC123"}],
                    "trackNumber": 1,
                    "duration_seconds": 180,
                }
            ],
        }
    )


class TestExtractTrack:
    """Tests for extract_track method."""

    def test_extracts_atv_track_with_album(
        self, atv_track: PlaylistTrack, sample_album: Album
    ) -> None:
        """Should extract ATV track and enrich with album metadata."""
        client = MockClientForTrack(track=atv_track, album=sample_album)
        extractor = MetadataExtractorService(client)

        result = extractor.extract_track(
            "https://music.youtube.com/watch?v=Vgpv5PtWsn4"
        )

        assert result is not None
        assert result.track.title == "A COLD PLAY"
        assert result.track.year == "2025"
        assert result.track.track_number == 1
        assert result.track.video_type == VideoType.ATV
        assert result.playlist_info.kind == ContentKind.TRACK
        assert client.get_track_calls == ["Vgpv5PtWsn4"]
        assert client.get_album_calls == ["MPREb_123"]

    def test_returns_none_for_ugc_track(self) -> None:
        """Should return None for UGC (non-music) tracks."""
        ugc_track = PlaylistTrack.model_validate(
            {
                "videoId": "jNQXAC9IVRw",
                "videoType": "MUSIC_VIDEO_TYPE_UGC",
                "title": "Me at the zoo",
                "artists": [{"name": "jawed", "id": None}],
                "album": None,
                "thumbnails": [
                    {"url": "https://example.com/thumb.jpg", "width": 120, "height": 90}
                ],
                "duration_seconds": 19,
            }
        )
        client = MockClientForTrack(track=ugc_track)
        extractor = MetadataExtractorService(client)

        result = extractor.extract_track("https://youtube.com/watch?v=jNQXAC9IVRw")

        assert result is None

    def test_extracts_omv_track_with_search(self) -> None:
        """Should extract OMV track and find album via search."""
        omv_track = PlaylistTrack.model_validate(
            {
                "videoId": "34Na4j8AVgA",
                "videoType": "MUSIC_VIDEO_TYPE_OMV",
                "title": "Starboy",
                "artists": [{"name": "The Weeknd", "id": "UC456"}],
                "album": None,
                "thumbnails": [
                    {
                        "url": "https://example.com/thumb.jpg",
                        "width": 544,
                        "height": 544,
                    }
                ],
                "duration_seconds": 230,
            }
        )
        starboy_album = Album.model_validate(
            {
                "title": "Starboy",
                "artists": [{"name": "The Weeknd", "id": "UC456"}],
                "year": "2016",
                "thumbnails": [
                    {
                        "url": "https://example.com/album.jpg",
                        "width": 544,
                        "height": 544,
                    }
                ],
                "tracks": [
                    {
                        "videoId": "plnfIj7dkJE",
                        "title": "Starboy",
                        "artists": [{"name": "The Weeknd", "id": "UC456"}],
                        "trackNumber": 1,
                        "duration_seconds": 230,
                    }
                ],
            }
        )

        class MockClientWithSearch(MockClientForTrack):
            """Mock that returns search results and handles album lookup."""

            def __init__(self, track: PlaylistTrack, album: Album) -> None:
                super().__init__(track=track, album=album)
                self._albums: dict[str, Album] = {"MPREb_starboy": album}

            def search_songs(self, query: str) -> list[SearchResult]:
                self.search_songs_calls.append(query)
                return [
                    SearchResult.model_validate(
                        {
                            "videoId": "plnfIj7dkJE",
                            "videoType": "MUSIC_VIDEO_TYPE_ATV",
                            "title": "Starboy",
                            "artists": [{"name": "The Weeknd", "id": "UC456"}],
                            "album": {"id": "MPREb_starboy", "name": "Starboy"},
                        }
                    )
                ]

            def get_album(self, album_id: str) -> Album:
                self.get_album_calls.append(album_id)
                if album_id in self._albums:
                    return self._albums[album_id]
                raise ValueError(f"Album not found: {album_id}")

        client = MockClientWithSearch(track=omv_track, album=starboy_album)
        extractor = MetadataExtractorService(client)

        result = extractor.extract_track(
            "https://music.youtube.com/watch?v=34Na4j8AVgA"
        )

        assert result is not None
        assert result.track.title == "Starboy"
        assert result.track.video_type == VideoType.OMV
        # Note: omv_video_id comes from album track (ATV) due to resolution logic
        # atv_video_id comes from search results
        assert result.track.atv_video_id == "plnfIj7dkJE"
        assert result.track.year == "2016"
        assert result.track.track_number == 1
        assert client.search_songs_calls == ["The Weeknd Starboy"]
        assert client.get_album_calls == ["MPREb_starboy"]

    def test_raises_for_invalid_url(self) -> None:
        """Should raise TrackParseError for invalid URL."""
        client = MockClientForTrack()
        extractor = MetadataExtractorService(client)

        with pytest.raises(TrackParseError, match="Could not extract video ID"):
            extractor.extract_track("https://music.youtube.com/playlist?list=PL123")

    def test_raises_for_empty_url(self) -> None:
        """Should raise TrackParseError for empty URL."""
        client = MockClientForTrack()
        extractor = MetadataExtractorService(client)

        with pytest.raises(TrackParseError, match="Could not extract video ID"):
            extractor.extract_track("")
