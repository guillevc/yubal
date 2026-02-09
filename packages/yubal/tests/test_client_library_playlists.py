"""Tests for YTMusicClient.get_library_playlists()."""

from unittest.mock import MagicMock

import pytest
from ytmusicapi.exceptions import YTMusicServerError, YTMusicUserError

from yubal.client import YTMusicClient
from yubal.exceptions import APIError, AuthenticationRequiredError


class TestGetLibraryPlaylists:
    def test_fetches_library_playlists_with_limit_none(self) -> None:
        mock_ytm = MagicMock()
        mock_ytm.get_library_playlists.return_value = [
            {
                "playlistId": "PLabc123",
                "title": "Morning Mix",
                "count": "24 songs",
                "thumbnails": [
                    {
                        "url": "https://example.com/thumb.jpg",
                        "width": 120,
                        "height": 120,
                    }
                ],
            }
        ]
        client = YTMusicClient(ytmusic=mock_ytm)

        playlists = client.get_library_playlists()

        assert len(playlists) == 1
        assert playlists[0].playlist_id == "PLabc123"
        assert playlists[0].title == "Morning Mix"
        assert playlists[0].track_count_raw == "24 songs"
        mock_ytm.get_library_playlists.assert_called_once_with(limit=None)

    def test_raises_authentication_required_on_auth_error(self) -> None:
        mock_ytm = MagicMock()
        mock_ytm.get_library_playlists.side_effect = YTMusicUserError(
            "Authentication is required"
        )
        client = YTMusicClient(ytmusic=mock_ytm)

        with pytest.raises(AuthenticationRequiredError):
            client.get_library_playlists()

    def test_raises_api_error_on_server_error(self) -> None:
        mock_ytm = MagicMock()
        mock_ytm.get_library_playlists.side_effect = YTMusicServerError(
            "Upstream fail"
        )
        client = YTMusicClient(ytmusic=mock_ytm)

        with pytest.raises(APIError, match="Failed to fetch library playlists"):
            client.get_library_playlists()
