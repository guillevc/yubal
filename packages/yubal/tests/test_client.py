"""Tests for YTMusicClient."""

from unittest.mock import MagicMock

import pytest
from yubal.client import YTMusicClient
from yubal.exceptions import APIError, TrackNotFoundError

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_ytmusic() -> MagicMock:
    """Create a mock YTMusic instance."""
    return MagicMock()


@pytest.fixture
def sample_album_data() -> dict:
    """Create sample album API response data."""
    return {
        "title": "Test Album",
        "artists": [{"name": "Test Artist", "id": "artist123"}],
        "year": "2024",
        "thumbnails": [
            {"url": "https://example.com/thumb.jpg", "width": 544, "height": 544}
        ],
        "tracks": [
            {
                "videoId": "video123",
                "title": "Test Song",
                "artists": [{"name": "Test Artist", "id": "artist123"}],
                "trackNumber": 1,
                "duration_seconds": 240,
            }
        ],
    }


# ============================================================================
# Album Caching Tests
# ============================================================================


class TestAlbumCaching:
    """Tests for album caching in YTMusicClient."""

    def test_caches_album_on_first_fetch(
        self, mock_ytmusic: MagicMock, sample_album_data: dict
    ) -> None:
        """Should cache album after first fetch."""
        mock_ytmusic.get_album.return_value = sample_album_data
        client = YTMusicClient(ytmusic=mock_ytmusic)

        assert client.get_album_cache_size() == 0

        client.get_album("album123")

        assert client.get_album_cache_size() == 1

    def test_returns_cached_album_on_second_fetch(
        self, mock_ytmusic: MagicMock, sample_album_data: dict
    ) -> None:
        """Should return cached album without API call on second fetch."""
        mock_ytmusic.get_album.return_value = sample_album_data
        client = YTMusicClient(ytmusic=mock_ytmusic)

        # First fetch
        album1 = client.get_album("album123")
        # Second fetch
        album2 = client.get_album("album123")

        assert album1.title == album2.title
        # API should only be called once
        assert mock_ytmusic.get_album.call_count == 1

    def test_different_albums_cached_separately(
        self, mock_ytmusic: MagicMock, sample_album_data: dict
    ) -> None:
        """Should cache different albums separately."""
        album_data_2 = {
            **sample_album_data,
            "title": "Another Album",
        }
        mock_ytmusic.get_album.side_effect = [sample_album_data, album_data_2]
        client = YTMusicClient(ytmusic=mock_ytmusic)

        album1 = client.get_album("album123")
        album2 = client.get_album("album456")

        assert album1.title == "Test Album"
        assert album2.title == "Another Album"
        assert client.get_album_cache_size() == 2
        assert mock_ytmusic.get_album.call_count == 2

    def test_clear_album_cache(
        self, mock_ytmusic: MagicMock, sample_album_data: dict
    ) -> None:
        """Should clear all cached albums."""
        mock_ytmusic.get_album.return_value = sample_album_data
        client = YTMusicClient(ytmusic=mock_ytmusic)

        client.get_album("album123")
        assert client.get_album_cache_size() == 1

        client.clear_album_cache()
        assert client.get_album_cache_size() == 0

    def test_refetches_after_cache_clear(
        self, mock_ytmusic: MagicMock, sample_album_data: dict
    ) -> None:
        """Should refetch album after cache is cleared."""
        mock_ytmusic.get_album.return_value = sample_album_data
        client = YTMusicClient(ytmusic=mock_ytmusic)

        client.get_album("album123")
        client.clear_album_cache()
        client.get_album("album123")

        # API should be called twice (once before clear, once after)
        assert mock_ytmusic.get_album.call_count == 2

    def test_cache_is_per_client_instance(
        self, mock_ytmusic: MagicMock, sample_album_data: dict
    ) -> None:
        """Cache should be isolated per client instance."""
        mock_ytmusic.get_album.return_value = sample_album_data
        client1 = YTMusicClient(ytmusic=mock_ytmusic)
        client2 = YTMusicClient(ytmusic=mock_ytmusic)

        client1.get_album("album123")

        assert client1.get_album_cache_size() == 1
        assert client2.get_album_cache_size() == 0


# ============================================================================
# Duration Parsing Tests
# ============================================================================


class TestParseDuration:
    """Tests for duration parsing in YTMusicClient."""

    @pytest.mark.parametrize(
        "length,expected",
        [
            ("3:00", 180),
            ("0:30", 30),
            ("10:00", 600),
            ("59:59", 3599),
            ("1:23:45", 5025),
            ("2:30:00", 9000),
            ("0:00", 0),
            ("0:0:0", 0),
        ],
    )
    def test_valid_durations(self, length: str, expected: int) -> None:
        client = YTMusicClient(ytmusic=MagicMock())
        assert client._parse_duration(length) == expected

    def test_single_part_returns_zero(self) -> None:
        client = YTMusicClient(ytmusic=MagicMock())
        assert client._parse_duration("180") == 0

    def test_four_parts_returns_zero(self) -> None:
        client = YTMusicClient(ytmusic=MagicMock())
        assert client._parse_duration("1:2:3:4") == 0

    def test_invalid_format_returns_zero(self) -> None:
        client = YTMusicClient(ytmusic=MagicMock())
        assert client._parse_duration("abc:def") == 0

    def test_empty_string_returns_zero(self) -> None:
        client = YTMusicClient(ytmusic=MagicMock())
        assert client._parse_duration("") == 0


# ============================================================================
# get_track() Tests
# ============================================================================


class TestGetTrack:
    def test_returns_playlist_track_for_valid_video_id(self) -> None:
        mock_ytm = MagicMock()
        mock_ytm.get_watch_playlist.return_value = {
            "tracks": [
                {
                    "videoId": "Vgpv5PtWsn4",
                    "title": "A COLD PLAY",
                    "artists": [{"name": "The Kid LAROI", "id": "UC123"}],
                    "album": {"name": "A COLD PLAY", "id": "MPREb_123"},
                    "videoType": "MUSIC_VIDEO_TYPE_ATV",
                    "thumbnails": [
                        {
                            "url": "https://example.com/thumb.jpg",
                            "width": 120,
                            "height": 120,
                        }
                    ],
                    "duration_seconds": 180,
                }
            ]
        }
        client = YTMusicClient(ytmusic=mock_ytm)
        track = client.get_track("Vgpv5PtWsn4")
        assert track.video_id == "Vgpv5PtWsn4"
        assert track.title == "A COLD PLAY"
        mock_ytm.get_watch_playlist.assert_called_once_with("Vgpv5PtWsn4")

    def test_raises_for_empty_video_id(self) -> None:
        client = YTMusicClient(ytmusic=MagicMock())
        with pytest.raises(ValueError, match="video_id cannot be empty"):
            client.get_track("")

    def test_raises_track_not_found_for_empty_tracks(self) -> None:
        mock_ytm = MagicMock()
        mock_ytm.get_watch_playlist.return_value = {"tracks": []}
        client = YTMusicClient(ytmusic=mock_ytm)
        with pytest.raises(TrackNotFoundError, match="Track not found"):
            client.get_track("invalid123")

    def test_raises_track_not_found_for_none_tracks(self) -> None:
        mock_ytm = MagicMock()
        mock_ytm.get_watch_playlist.return_value = {"tracks": None}
        client = YTMusicClient(ytmusic=mock_ytm)
        with pytest.raises(TrackNotFoundError, match="Track not found"):
            client.get_track("invalid123")

    def test_raises_api_error_on_exception(self) -> None:
        from ytmusicapi.exceptions import YTMusicServerError

        mock_ytm = MagicMock()
        mock_ytm.get_watch_playlist.side_effect = YTMusicServerError("API failure")
        client = YTMusicClient(ytmusic=mock_ytm)
        with pytest.raises(APIError, match="Failed to fetch track"):
            client.get_track("abc123")

    def test_normalizes_watch_playlist_response_format(self) -> None:
        """Should normalize thumbnail->thumbnails and length->duration_seconds."""
        mock_ytm = MagicMock()
        mock_ytm.get_watch_playlist.return_value = {
            "tracks": [
                {
                    "videoId": "Vgpv5PtWsn4",
                    "title": "A COLD PLAY",
                    "artists": [{"name": "The Kid LAROI", "id": "UC123"}],
                    "album": {"name": "A COLD PLAY", "id": "MPREb_123"},
                    "videoType": "MUSIC_VIDEO_TYPE_ATV",
                    "thumbnail": [
                        {
                            "url": "https://example.com/thumb.jpg",
                            "width": 544,
                            "height": 544,
                        }
                    ],
                    "length": "3:00",
                }
            ]
        }
        client = YTMusicClient(ytmusic=mock_ytm)
        track = client.get_track("Vgpv5PtWsn4")
        assert track.video_id == "Vgpv5PtWsn4"
        assert track.duration_seconds == 180
        assert len(track.thumbnails) == 1
        assert track.thumbnails[0].url == "https://example.com/thumb.jpg"
