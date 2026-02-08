"""Tests for YTMusicClient.get_track() and duration parsing."""

from unittest.mock import MagicMock

import pytest
from yubal.client import YTMusicClient
from yubal.exceptions import APIError, TrackNotFoundError


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


class TestGetPlaylist:
    def test_normalizes_null_artists_to_empty_list(self) -> None:
        mock_ytm = MagicMock()
        mock_ytm.get_playlist.return_value = {
            "title": "Liked Music",
            "tracks": [
                {
                    "videoId": "abc123",
                    "videoType": "MUSIC_VIDEO_TYPE_ATV",
                    "title": "Track With Null Artists",
                    "artists": None,
                    "thumbnails": [
                        {
                            "url": "https://example.com/thumb.jpg",
                            "width": 120,
                            "height": 120,
                        }
                    ],
                    "duration_seconds": 180,
                }
            ],
        }

        client = YTMusicClient(ytmusic=mock_ytm)

        playlist = client.get_playlist("LM")

        assert len(playlist.tracks) == 1
        assert playlist.tracks[0].artists == []
