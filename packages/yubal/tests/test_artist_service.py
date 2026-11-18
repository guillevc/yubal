"""Tests for artist search/discography (client methods + ArtistDiscographyService)."""

from typing import Any
from unittest.mock import MagicMock

import pytest
from conftest import MockYTMusicClient
from ytmusicapi.exceptions import YTMusicServerError
from yubal.client import YTMusicClient
from yubal.exceptions import ArtistNotFoundError, UpstreamAPIError
from yubal.models.ytmusic import (
    ArtistDiscography,
    ArtistRelease,
    ArtistSearchResult,
)
from yubal.services import ArtistDiscographyService

# ============================================================================
# Helpers
# ============================================================================


def _album_item(
    title: str, browse_id: str, playlist_id: str | None, **extra: Any
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "title": title,
        "type": "Album",
        "year": "2020",
        "browseId": browse_id,
        "thumbnails": [{"url": "https://x/t.jpg", "width": 60, "height": 60}],
        **extra,
    }
    if playlist_id is not None:
        item["audioPlaylistId"] = playlist_id
    return item


def _album_payload(playlist_id: str | None) -> dict[str, Any]:
    """Minimal get_album() response."""
    return {
        "title": "Some Single",
        "artists": [{"name": "Artist", "id": "UC1"}],
        "thumbnails": [],
        "tracks": [],
        "audioPlaylistId": playlist_id,
    }


@pytest.fixture
def ytm() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(ytm: MagicMock) -> YTMusicClient:
    return YTMusicClient(ytmusic=ytm)


# ============================================================================
# YTMusicClient.search_artists
# ============================================================================


class TestSearchArtists:
    def test_parses_artist_results(self, ytm: MagicMock, client: YTMusicClient) -> None:
        ytm.search.return_value = [
            {
                "resultType": "artist",
                "artist": "Daft Punk",
                "browseId": "UC1",
                "thumbnails": [{"url": "https://x/a.jpg", "width": 60, "height": 60}],
            },
            {"resultType": "artist", "artist": "Thomas Bangalter", "browseId": "UC2"},
        ]

        results = client.search_artists("daft punk", limit=5)

        ytm.search.assert_called_once_with("daft punk", filter="artists", limit=5)
        assert [r.artist for r in results] == ["Daft Punk", "Thomas Bangalter"]
        assert results[0].browse_id == "UC1"
        assert results[0].thumbnails[0].url == "https://x/a.jpg"

    def test_skips_non_artist_and_incomplete_entries(
        self, ytm: MagicMock, client: YTMusicClient
    ) -> None:
        ytm.search.return_value = [
            {"resultType": "album", "artist": "X", "browseId": "MPREb_1"},
            {"resultType": "artist", "artist": "No Id"},
            {"resultType": "artist", "artist": "Ok", "browseId": "UC3"},
        ]

        results = client.search_artists("x")

        assert [r.browse_id for r in results] == ["UC3"]

    def test_respects_limit(self, ytm: MagicMock, client: YTMusicClient) -> None:
        ytm.search.return_value = [
            {"resultType": "artist", "artist": f"A{i}", "browseId": f"UC{i}"}
            for i in range(10)
        ]

        assert len(client.search_artists("a", limit=3)) == 3

    def test_empty_query_raises(self, client: YTMusicClient) -> None:
        with pytest.raises(ValueError):
            client.search_artists("   ")

    def test_wraps_api_errors(self, ytm: MagicMock, client: YTMusicClient) -> None:
        ytm.search.side_effect = YTMusicServerError("boom")

        with pytest.raises(UpstreamAPIError):
            client.search_artists("x")


# ============================================================================
# YTMusicClient.get_artist
# ============================================================================


class TestGetArtist:
    def test_uses_artist_page_results_when_complete(
        self, ytm: MagicMock, client: YTMusicClient
    ) -> None:
        ytm.get_artist.return_value = {
            "name": "Artist",
            "albums": {"results": [_album_item("A1", "MPREb_a1", "OLAK_a1")]},
            "singles": {"results": [_album_item("S1", "MPREb_s1", "OLAK_s1")]},
        }

        discography = client.get_artist("UC1")

        ytm.get_artist_albums.assert_not_called()
        assert discography.name == "Artist"
        assert discography.channel_id == "UC1"
        assert [a.audio_playlist_id for a in discography.albums] == ["OLAK_a1"]
        assert [s.audio_playlist_id for s in discography.singles] == ["OLAK_s1"]

    def test_fetches_full_list_when_section_has_more(
        self, ytm: MagicMock, client: YTMusicClient
    ) -> None:
        ytm.get_artist.return_value = {
            "name": "Artist",
            "albums": {
                "results": [_album_item("A1", "MPREb_a1", "OLAK_a1")],
                "browseId": "UC1",
                "params": "albums-params",
            },
        }
        # get_artist_albums returns "playlistId" rather than "audioPlaylistId"
        ytm.get_artist_albums.return_value = [
            {"title": "A1", "browseId": "MPREb_a1", "playlistId": "OLAK_a1"},
            {"title": "A2", "browseId": "MPREb_a2", "playlistId": "OLAK_a2"},
        ]

        discography = client.get_artist("UC1")

        ytm.get_artist_albums.assert_called_once_with(
            "UC1", "albums-params", limit=None
        )
        assert [a.title for a in discography.albums] == ["A1", "A2"]
        assert discography.albums[1].url == (
            "https://music.youtube.com/playlist?list=OLAK_a2"
        )

    def test_falls_back_to_page_results_if_full_list_fails(
        self, ytm: MagicMock, client: YTMusicClient
    ) -> None:
        ytm.get_artist.return_value = {
            "name": "Artist",
            "albums": {
                "results": [_album_item("A1", "MPREb_a1", "OLAK_a1")],
                "browseId": "UC1",
                "params": "p",
            },
        }
        ytm.get_artist_albums.side_effect = YTMusicServerError("boom")

        discography = client.get_artist("UC1")

        assert [a.title for a in discography.albums] == ["A1"]

    def test_resolves_missing_playlist_id_via_get_album(
        self, ytm: MagicMock, client: YTMusicClient
    ) -> None:
        ytm.get_artist.return_value = {
            "name": "Artist",
            "singles": {"results": [_album_item("S1", "MPREb_s1", None)]},
        }
        ytm.get_album.return_value = _album_payload("OLAK_s1")

        discography = client.get_artist("UC1")

        ytm.get_album.assert_called_once_with("MPREb_s1")
        assert discography.singles[0].audio_playlist_id == "OLAK_s1"

    def test_drops_releases_that_cannot_be_resolved(
        self, ytm: MagicMock, client: YTMusicClient
    ) -> None:
        ytm.get_artist.return_value = {
            "name": "Artist",
            "singles": {
                "results": [
                    _album_item("No playlist", "MPREb_s1", None),
                    _album_item("Error", "MPREb_s2", None),
                    _album_item("Ok", "MPREb_s3", "OLAK_s3"),
                ]
            },
        }
        ytm.get_album.side_effect = [
            _album_payload(None),
            YTMusicServerError("boom"),
        ]

        discography = client.get_artist("UC1")

        assert [s.title for s in discography.singles] == ["Ok"]

    def test_deduplicates_across_sections(
        self, ytm: MagicMock, client: YTMusicClient
    ) -> None:
        ytm.get_artist.return_value = {
            "name": "Artist",
            "albums": {"results": [_album_item("A1", "MPREb_a1", "OLAK_1")]},
            "singles": {
                "results": [
                    _album_item("Same", "MPREb_a1", "OLAK_1"),
                    _album_item("S2", "MPREb_s2", "OLAK_2"),
                ]
            },
        }

        discography = client.get_artist("UC1")

        assert [a.title for a in discography.albums] == ["A1"]
        assert [s.title for s in discography.singles] == ["S2"]

    def test_missing_sections_are_empty(
        self, ytm: MagicMock, client: YTMusicClient
    ) -> None:
        ytm.get_artist.return_value = {"name": "Artist", "songs": {"results": []}}

        discography = client.get_artist("UC1")

        assert discography.albums == []
        assert discography.singles == []

    def test_skips_malformed_entries(
        self, ytm: MagicMock, client: YTMusicClient
    ) -> None:
        ytm.get_artist.return_value = {
            "name": "Artist",
            "albums": {
                "results": [
                    None,
                    {"title": "No browse id"},
                    _album_item("Bad thumbs", "MPREb_x", "OLAK_x", thumbnails=[{}]),
                    _album_item("Ok", "MPREb_ok", "OLAK_ok"),
                ]
            },
        }

        discography = client.get_artist("UC1")

        assert [a.title for a in discography.albums] == ["Ok"]

    def test_missing_name_raises_not_found(
        self, ytm: MagicMock, client: YTMusicClient
    ) -> None:
        ytm.get_artist.return_value = {}

        with pytest.raises(ArtistNotFoundError):
            client.get_artist("UC1")

    def test_malformed_response_raises_not_found(
        self, ytm: MagicMock, client: YTMusicClient
    ) -> None:
        ytm.get_artist.side_effect = KeyError("header")

        with pytest.raises(ArtistNotFoundError):
            client.get_artist("UC1")

    def test_wraps_api_errors(self, ytm: MagicMock, client: YTMusicClient) -> None:
        ytm.get_artist.side_effect = YTMusicServerError("boom")

        with pytest.raises(UpstreamAPIError):
            client.get_artist("UC1")

    def test_empty_channel_id_raises(self, client: YTMusicClient) -> None:
        with pytest.raises(ValueError):
            client.get_artist("")


# ============================================================================
# ArtistDiscographyService
# ============================================================================


def _release(title: str, playlist_id: str | None) -> ArtistRelease:
    return ArtistRelease.model_validate(
        {"title": title, "browseId": f"MPREb_{title}", "audioPlaylistId": playlist_id}
    )


@pytest.fixture
def discography() -> ArtistDiscography:
    return ArtistDiscography(
        name="Artist",
        channel_id="UC1",
        albums=[_release("A1", "OLAK_a1"), _release("A2", "OLAK_a2")],
        singles=[_release("S1", "OLAK_s1")],
    )


class TestArtistDiscographyService:
    def test_search_returns_results(self) -> None:
        match = ArtistSearchResult.model_validate(
            {"browseId": "UC1", "artist": "Artist"}
        )
        mock = MockYTMusicClient(artist_results=[match])

        results = ArtistDiscographyService(mock).search("artist")

        assert results == [match]
        assert mock.search_artists_calls == ["artist"]

    def test_search_raises_when_no_results(self) -> None:
        with pytest.raises(ArtistNotFoundError):
            ArtistDiscographyService(MockYTMusicClient()).search("nobody")

    def test_get_discography_all(self, discography: ArtistDiscography) -> None:
        service = ArtistDiscographyService(MockYTMusicClient(discography=discography))

        result = service.get_discography("UC1")

        assert result == discography

    def test_get_discography_filters_sections(
        self, discography: ArtistDiscography
    ) -> None:
        service = ArtistDiscographyService(MockYTMusicClient(discography=discography))

        albums_only = service.get_discography("UC1", singles=False)
        singles_only = service.get_discography("UC1", albums=False)

        assert len(albums_only.albums) == 2
        assert albums_only.singles == []
        assert singles_only.albums == []
        assert len(singles_only.singles) == 1

    def test_release_urls_albums_first(self, discography: ArtistDiscography) -> None:
        urls = ArtistDiscographyService.release_urls(discography)

        assert urls == [
            "https://music.youtube.com/playlist?list=OLAK_a1",
            "https://music.youtube.com/playlist?list=OLAK_a2",
            "https://music.youtube.com/playlist?list=OLAK_s1",
        ]

    def test_release_urls_skip_unresolved(self) -> None:
        discography = ArtistDiscography(
            name="Artist",
            channel_id="UC1",
            albums=[_release("A1", None), _release("A2", "OLAK_a2")],
        )

        urls = ArtistDiscographyService.release_urls(discography)

        assert urls == ["https://music.youtube.com/playlist?list=OLAK_a2"]
