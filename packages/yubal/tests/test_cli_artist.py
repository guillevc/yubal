"""Tests for the `yubal artist` CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner
from yubal.cli.main import app
from yubal.exceptions import ArtistNotFoundError, UpstreamAPIError
from yubal.models.ytmusic import (
    ArtistDiscography,
    ArtistRelease,
    ArtistSearchResult,
)

runner = CliRunner()


def _release(title: str) -> ArtistRelease:
    return ArtistRelease.model_validate(
        {
            "title": title,
            "browseId": f"MPREb_{title}",
            "audioPlaylistId": f"OLAK_{title}",
        }
    )


def _url(title: str) -> str:
    return f"https://music.youtube.com/playlist?list=OLAK_{title}"


@pytest.fixture
def artists() -> MagicMock:
    service = MagicMock()
    service.search.return_value = [
        ArtistSearchResult.model_validate({"browseId": "UC1", "artist": "First"}),
        ArtistSearchResult.model_validate({"browseId": "UC2", "artist": "Second"}),
    ]
    discography = ArtistDiscography(
        name="First",
        channel_id="UC1",
        albums=[_release("A1"), _release("A2")],
        singles=[_release("S1")],
    )
    service.get_discography.return_value = discography
    service.releases.return_value = [
        *discography.albums,
        *discography.singles,
    ]
    return service


@pytest.fixture
def run_download() -> MagicMock:
    result = MagicMock(success_count=2, skipped_count=1, failed_count=0)
    return MagicMock(return_value=result)


@pytest.fixture
def patched(artists: MagicMock, run_download: MagicMock) -> object:
    with (
        patch("yubal.cli.commands.artist.YTMusicClient"),
        patch(
            "yubal.cli.commands.artist.ArtistDiscographyService",
            return_value=artists,
        ),
        patch("yubal.cli.commands.artist.build_playlist_service"),
        patch("yubal.cli.commands.artist.run_playlist_download", run_download),
    ):
        yield


@pytest.mark.usefixtures("patched")
class TestArtistCommand:
    def test_downloads_every_release_in_order(
        self, tmp_path: Path, run_download: MagicMock
    ) -> None:
        result = runner.invoke(app, ["artist", "first", str(tmp_path), "--yes"])

        assert result.exit_code == 0, result.output
        urls = [c.args[2] for c in run_download.call_args_list]
        assert urls == [_url("A1"), _url("A2"), _url("S1")]
        assert "Downloaded: 6" in result.output

    def test_pick_selects_other_match(self, tmp_path: Path, artists: MagicMock) -> None:
        result = runner.invoke(
            app, ["artist", "x", str(tmp_path), "--pick", "2", "--yes"]
        )

        assert result.exit_code == 0, result.output
        artists.get_discography.assert_called_once_with(
            "UC2", albums=True, singles=True
        )

    def test_pick_out_of_range_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["artist", "x", str(tmp_path), "--pick", "9", "--yes"]
        )

        assert result.exit_code == 1

    def test_section_filters_are_passed(
        self, tmp_path: Path, artists: MagicMock
    ) -> None:
        runner.invoke(app, ["artist", "x", str(tmp_path), "--no-singles", "--yes"])

        artists.get_discography.assert_called_once_with(
            "UC1", albums=True, singles=False
        )

    def test_excluding_everything_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(
            app, ["artist", "x", str(tmp_path), "--no-albums", "--no-singles"]
        )

        assert result.exit_code == 1

    def test_declining_prompt_downloads_nothing(
        self, tmp_path: Path, run_download: MagicMock
    ) -> None:
        result = runner.invoke(app, ["artist", "x", str(tmp_path)], input="n\n")

        assert result.exit_code != 0
        run_download.assert_not_called()

    def test_accepting_prompt_downloads(
        self, tmp_path: Path, run_download: MagicMock
    ) -> None:
        result = runner.invoke(app, ["artist", "x", str(tmp_path)], input="y\n")

        assert result.exit_code == 0, result.output
        assert run_download.call_count == 3

    def test_failed_release_does_not_stop_others(
        self, tmp_path: Path, run_download: MagicMock
    ) -> None:
        ok = MagicMock(success_count=1, skipped_count=0, failed_count=0)
        run_download.side_effect = [ok, UpstreamAPIError("boom"), ok]

        result = runner.invoke(app, ["artist", "x", str(tmp_path), "--yes"])

        assert run_download.call_count == 3
        assert result.exit_code == 1
        assert "A2: boom" in result.output

    def test_no_artist_found(self, tmp_path: Path, artists: MagicMock) -> None:
        artists.search.side_effect = ArtistNotFoundError("No artists found for: x")

        result = runner.invoke(app, ["artist", "x", str(tmp_path), "--yes"])

        assert result.exit_code == 1
        assert "No artists found" in result.output
