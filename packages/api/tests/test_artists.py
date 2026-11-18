"""Tests for artist API routes."""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from yubal import (
    ArtistDiscography,
    ArtistNotFoundError,
    ArtistRelease,
    ArtistSearchResult,
)
from yubal_api.api import deps
from yubal_api.api.exceptions import register_exception_handlers
from yubal_api.api.routes import artists

# TestClient's event loop needs a local socketpair; no network is used.
pytestmark = pytest.mark.enable_socket

ALBUM_URL = "https://music.youtube.com/playlist?list=OLAK5uy_album1"
SINGLE_URL = "https://music.youtube.com/playlist?list=OLAK5uy_single1"


def _release(title: str, playlist_id: str | None) -> ArtistRelease:
    return ArtistRelease.model_validate(
        {
            "title": title,
            "type": "Album",
            "year": "2001",
            "browseId": f"MPREb_{title}",
            "audioPlaylistId": playlist_id,
            "thumbnails": [
                {"url": "https://x/small.jpg", "width": 60, "height": 60},
                {"url": "https://x/large.jpg", "width": 544, "height": 544},
            ],
        }
    )


@pytest.fixture
def artist_service() -> MagicMock:
    return MagicMock()


@pytest.fixture
def job_executor() -> MagicMock:
    return MagicMock()


@pytest.fixture
def client(artist_service: MagicMock, job_executor: MagicMock) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(artists.router)
    app.dependency_overrides[deps._get_artist_service] = lambda: artist_service
    app.dependency_overrides[deps._get_job_executor] = lambda: job_executor
    return TestClient(app)


class TestSearchArtists:
    def test_returns_matches(
        self, client: TestClient, artist_service: MagicMock
    ) -> None:
        artist_service.search.return_value = [
            ArtistSearchResult.model_validate(
                {
                    "browseId": "UC1",
                    "artist": "Daft Punk",
                    "thumbnails": [
                        {"url": "https://x/a.jpg", "width": 120, "height": 120}
                    ],
                }
            )
        ]

        response = client.get("/artists/search", params={"q": "daft punk"})

        assert response.status_code == 200
        assert response.json() == {
            "artists": [
                {
                    "channel_id": "UC1",
                    "name": "Daft Punk",
                    "thumbnail_url": "https://x/a.jpg",
                }
            ]
        }
        artist_service.search.assert_called_once_with("daft punk")

    def test_no_results_is_404(
        self, client: TestClient, artist_service: MagicMock
    ) -> None:
        artist_service.search.side_effect = ArtistNotFoundError("none")

        response = client.get("/artists/search", params={"q": "zzz"})

        assert response.status_code == 404
        assert response.json()["error"] == "artist_not_found"

    def test_requires_query(self, client: TestClient) -> None:
        assert client.get("/artists/search").status_code == 422


class TestGetArtistReleases:
    def test_returns_releases_with_urls(
        self, client: TestClient, artist_service: MagicMock
    ) -> None:
        artist_service.get_discography.return_value = ArtistDiscography(
            name="Daft Punk",
            channel_id="UC1",
            albums=[_release("Discovery", "OLAK5uy_album1")],
            singles=[_release("Unresolved", None)],
        )

        response = client.get("/artists/UC1/releases")

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Daft Punk"
        assert body["albums"] == [
            {
                "title": "Discovery",
                "type": "Album",
                "year": "2001",
                "url": ALBUM_URL,
                "thumbnail_url": "https://x/large.jpg",
            }
        ]
        # Releases without a playlist URL are omitted
        assert body["singles"] == []

    def test_unknown_artist_is_404(
        self, client: TestClient, artist_service: MagicMock
    ) -> None:
        artist_service.get_discography.side_effect = ArtistNotFoundError("nope")

        assert client.get("/artists/UCx/releases").status_code == 404


class TestQueueArtistReleases:
    def test_creates_one_job_per_url(
        self, client: TestClient, job_executor: MagicMock
    ) -> None:
        job_executor.create_and_start_job.side_effect = [
            MagicMock(id="job-1"),
            MagicMock(id="job-2"),
        ]

        response = client.post("/artists/jobs", json={"urls": [ALBUM_URL, SINGLE_URL]})

        assert response.status_code == 201
        assert response.json() == {"job_ids": ["job-1", "job-2"], "skipped": 0}
        assert [
            c.args[0] for c in job_executor.create_and_start_job.call_args_list
        ] == [
            ALBUM_URL,
            SINGLE_URL,
        ]

    def test_reports_skipped_when_queue_fills(
        self, client: TestClient, job_executor: MagicMock
    ) -> None:
        job_executor.create_and_start_job.side_effect = [MagicMock(id="job-1"), None]

        response = client.post(
            "/artists/jobs", json={"urls": [ALBUM_URL, SINGLE_URL, ALBUM_URL]}
        )

        assert response.status_code == 201
        assert response.json() == {"job_ids": ["job-1"], "skipped": 2}
        assert job_executor.create_and_start_job.call_count == 2

    def test_queue_full_is_409(
        self, client: TestClient, job_executor: MagicMock
    ) -> None:
        job_executor.create_and_start_job.return_value = None

        response = client.post("/artists/jobs", json={"urls": [ALBUM_URL]})

        assert response.status_code == 409

    def test_rejects_invalid_urls(
        self, client: TestClient, job_executor: MagicMock
    ) -> None:
        response = client.post(
            "/artists/jobs", json={"urls": ["https://example.com/nope"]}
        )

        assert response.status_code == 422
        job_executor.create_and_start_job.assert_not_called()

    def test_rejects_empty_list(self, client: TestClient) -> None:
        assert client.post("/artists/jobs", json={"urls": []}).status_code == 422
