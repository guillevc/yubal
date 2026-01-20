"""Tests for data models."""

import pytest
from pydantic import ValidationError
from yubal.models.domain import TrackMetadata, VideoType
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


class TestVideoType:
    """Tests for VideoType enum."""

    def test_atv_value(self) -> None:
        """ATV should have correct value matching ytmusicapi."""
        assert VideoType.ATV == "MUSIC_VIDEO_TYPE_ATV"

    def test_omv_value(self) -> None:
        """OMV should have correct value matching ytmusicapi."""
        assert VideoType.OMV == "MUSIC_VIDEO_TYPE_OMV"

    def test_string_comparison(self) -> None:
        """Should compare equal to ytmusicapi string values."""
        assert VideoType.ATV == "MUSIC_VIDEO_TYPE_ATV"
        assert VideoType.OMV == "MUSIC_VIDEO_TYPE_OMV"

    def test_all_video_types(self) -> None:
        """All video types should have correct values."""
        assert VideoType.ATV == "MUSIC_VIDEO_TYPE_ATV"
        assert VideoType.OMV == "MUSIC_VIDEO_TYPE_OMV"
        assert (
            VideoType.OFFICIAL_SOURCE_MUSIC == "MUSIC_VIDEO_TYPE_OFFICIAL_SOURCE_MUSIC"
        )
        assert VideoType.UGC == "MUSIC_VIDEO_TYPE_UGC"

    def test_parse_from_api_string(self) -> None:
        """Should parse from ytmusicapi raw string values."""
        assert VideoType("MUSIC_VIDEO_TYPE_ATV") == VideoType.ATV
        assert VideoType("MUSIC_VIDEO_TYPE_OMV") == VideoType.OMV
        assert VideoType("MUSIC_VIDEO_TYPE_UGC") == VideoType.UGC


class TestTrackMetadata:
    """Tests for TrackMetadata model."""

    def test_minimal_creation(self) -> None:
        """Should create with minimal required fields."""
        track = TrackMetadata(
            omv_video_id="abc123",
            title="Test Song",
            artists=["Test Artist"],
            album="Test Album",
            album_artists=["Test Artist"],
            video_type=VideoType.ATV,
        )
        assert track.omv_video_id == "abc123"
        assert track.atv_video_id is None
        assert track.track_number is None

    def test_full_creation(self) -> None:
        """Should create with all fields."""
        track = TrackMetadata(
            omv_video_id="omv123",
            atv_video_id="atv123",
            title="Test Song",
            artists=["Artist One", "Artist Two"],
            album="Test Album",
            album_artists=["Various Artists"],
            track_number=5,
            year="2024",
            cover_url="https://example.com/cover.jpg",
            video_type=VideoType.OMV,
        )
        assert track.atv_video_id == "atv123"
        assert track.track_number == 5
        assert track.year == "2024"
        # Test computed properties
        assert track.artist == "Artist One; Artist Two"
        assert track.album_artist == "Various Artists"
        assert track.primary_album_artist == "Various Artists"

    def test_model_dump(self) -> None:
        """Should serialize to dict correctly."""
        track = TrackMetadata(
            omv_video_id="abc123",
            title="Test",
            artists=["Artist"],
            album="Album",
            album_artists=["Artist"],
            video_type=VideoType.ATV,
        )
        data = track.model_dump()
        assert data["omv_video_id"] == "abc123"
        assert data["video_type"] == "MUSIC_VIDEO_TYPE_ATV"
        assert data["artists"] == ["Artist"]
        assert data["album_artists"] == ["Artist"]

    def test_primary_album_artist_empty_list(self) -> None:
        """Should return 'Unknown Artist' when album_artists is empty."""
        track = TrackMetadata(
            omv_video_id="abc123",
            title="Test",
            artists=["Artist"],
            album="Album",
            album_artists=[],
            video_type=VideoType.ATV,
        )
        assert track.primary_album_artist == "Unknown Artist"


class TestYTMusicModels:
    """Tests for ytmusicapi response models."""

    def test_artist_with_alias(self) -> None:
        """Artist should parse correctly."""
        artist = Artist(name="Test", id="123")
        assert artist.name == "Test"
        assert artist.id == "123"

    def test_artist_without_id(self) -> None:
        """Artist should work without ID."""
        artist = Artist(name="Test", id=None)
        assert artist.id is None

    def test_thumbnail_validation(self) -> None:
        """Thumbnail should validate dimensions."""
        thumb = Thumbnail(url="https://test.jpg", width=544, height=544)
        assert thumb.width == 544

    def test_album_ref_from_dict(self) -> None:
        """AlbumRef should parse from dict."""
        ref = AlbumRef.model_validate({"id": "abc", "name": "Album Name"})
        assert ref.id == "abc"
        assert ref.name == "Album Name"

    def test_playlist_track_with_alias(self) -> None:
        """PlaylistTrack should parse videoId alias."""
        track = PlaylistTrack.model_validate(
            {
                "videoId": "vid123",
                "title": "Song",
                "artists": [{"name": "Artist", "id": "a1"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 120, "height": 90}],
                "duration_seconds": 180,
            }
        )
        assert track.video_id == "vid123"

    def test_playlist_track_ignores_extra_fields(self) -> None:
        """PlaylistTrack should ignore unknown fields."""
        track = PlaylistTrack.model_validate(
            {
                "videoId": "vid123",
                "title": "Song",
                "artists": [{"name": "Artist", "id": "a1"}],
                "thumbnails": [{"url": "https://t.jpg", "width": 120, "height": 90}],
                "duration_seconds": 180,
                "unknownField": "should be ignored",
                "anotherUnknown": 123,
            }
        )
        assert track.video_id == "vid123"
        assert not hasattr(track, "unknownField")

    def test_album_track_with_aliases(self) -> None:
        """AlbumTrack should parse aliases correctly."""
        track = AlbumTrack.model_validate(
            {
                "videoId": "vid123",
                "title": "Song",
                "artists": [{"name": "Artist"}],
                "trackNumber": 5,
                "duration_seconds": 240,
            }
        )
        assert track.video_id == "vid123"
        assert track.track_number == 5

    def test_album_parsing(self) -> None:
        """Album should parse with nested tracks."""
        album = Album.model_validate(
            {
                "title": "Album Title",
                "artists": [{"name": "Artist"}],
                "year": "2024",
                "thumbnails": [{"url": "https://t.jpg", "width": 544, "height": 544}],
                "tracks": [
                    {
                        "videoId": "t1",
                        "title": "Track 1",
                        "artists": [{"name": "Artist"}],
                        "trackNumber": 1,
                        "duration_seconds": 200,
                    }
                ],
            }
        )
        assert album.title == "Album Title"
        assert len(album.tracks) == 1
        assert album.tracks[0].track_number == 1

    def test_playlist_parsing(self) -> None:
        """Playlist should parse with nested tracks."""
        playlist = Playlist.model_validate(
            {
                "tracks": [
                    {
                        "videoId": "v1",
                        "title": "Track",
                        "artists": [{"name": "Artist"}],
                        "thumbnails": [
                            {"url": "https://t.jpg", "width": 120, "height": 90}
                        ],
                        "duration_seconds": 180,
                    }
                ]
            }
        )
        assert len(playlist.tracks) == 1

    def test_search_result_parsing(self) -> None:
        """SearchResult should parse with optional album."""
        result = SearchResult.model_validate(
            {
                "videoId": "s1",
                "videoType": "MUSIC_VIDEO_TYPE_ATV",
                "album": {"id": "alb1", "name": "Album"},
            }
        )
        assert result.video_id == "s1"
        assert result.album is not None
        assert result.album.id == "alb1"

    def test_search_result_without_album(self) -> None:
        """SearchResult should work without album."""
        result = SearchResult.model_validate(
            {
                "videoId": "s1",
            }
        )
        assert result.album is None

    def test_models_are_frozen(self) -> None:
        """Models should be immutable."""
        artist = Artist(name="Test", id="123")
        with pytest.raises(ValidationError):
            artist.name = "Changed"
