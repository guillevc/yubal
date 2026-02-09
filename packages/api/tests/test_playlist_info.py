"""Tests for playlist info service and related route handlers."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from yubal import APIError, AuthenticationRequiredError
from yubal.models.ytmusic import LibraryPlaylist

from yubal_api.api.routes.subscriptions import list_library_playlists
from yubal_api.services.playlist_info import PlaylistInfoService


class TestPlaylistInfoServiceLibraryPlaylists:
    def test_list_library_playlists_normalizes_fields(self) -> None:
        service = PlaylistInfoService(cookies_path=None)
        service._client = MagicMock()
        service._client.get_library_playlists.return_value = [
            LibraryPlaylist.model_validate(
                {
                    "playlistId": "PL123",
                    "title": "My Mix",
                    "count": "24 songs",
                    "thumbnails": [
                        {
                            "url": "https://example.com/small.jpg",
                            "width": 120,
                            "height": 120,
                        },
                        {
                            "url": "https://example.com/large.jpg",
                            "width": 544,
                            "height": 544,
                        },
                    ],
                }
            )
        ]

        result = service.list_library_playlists()

        assert len(result) == 1
        assert result[0].playlist_id == "PL123"
        assert result[0].title == "My Mix"
        assert result[0].name == "My Mix"
        assert result[0].url == "https://music.youtube.com/playlist?list=PL123"
        assert result[0].thumbnail_url == "https://example.com/large.jpg"
        assert result[0].track_count == 24

    @pytest.mark.parametrize(
        ("count", "expected"),
        [(7, 7), ("108 songs", 108), ("No tracks", None), (None, None)],
    )
    def test_parse_track_count(
        self,
        count: int | str | None,
        expected: int | None,
    ) -> None:
        service = PlaylistInfoService(cookies_path=None)
        assert service._parse_track_count(count) == expected


class TestListLibraryPlaylistsRoute:
    def test_returns_playlist_list_response(self) -> None:
        service = MagicMock()
        service.list_library_playlists.return_value = [
            {
                "playlist_id": "PL123",
                "title": "A",
                "name": "A",
                "url": "https://music.youtube.com/playlist?list=PL123",
                "thumbnail_url": None,
                "track_count": 5,
            }
        ]

        response = list_library_playlists(service)

        assert len(response.items) == 1
        assert response.items[0].playlist_id == "PL123"

    def test_maps_authentication_error_to_401(self) -> None:
        service = MagicMock()
        service.list_library_playlists.side_effect = AuthenticationRequiredError(
            "auth"
        )

        with pytest.raises(HTTPException) as exc_info:
            list_library_playlists(service)

        assert exc_info.value.status_code == 401

    def test_maps_api_error_to_502(self) -> None:
        service = MagicMock()
        service.list_library_playlists.side_effect = APIError("upstream")

        with pytest.raises(HTTPException) as exc_info:
            list_library_playlists(service)

        assert exc_info.value.status_code == 502
