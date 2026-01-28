"""Tests for PlaylistArtifactsService."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from yubal.models.enums import ContentKind, DownloadStatus, VideoType
from yubal.models.results import DownloadResult
from yubal.models.track import PlaylistInfo, TrackMetadata
from yubal.services.artifacts import PlaylistArtifactsService


@pytest.fixture
def composer() -> PlaylistArtifactsService:
    """Create a composer service instance."""
    return PlaylistArtifactsService()


@pytest.fixture
def playlist_info() -> PlaylistInfo:
    """Create sample playlist info."""
    return PlaylistInfo(
        playlist_id="PLtest123",
        title="Test Playlist",
        cover_url="https://example.com/cover.jpg",
        kind=ContentKind.PLAYLIST,
    )


@pytest.fixture
def album_playlist_info() -> PlaylistInfo:
    """Create sample album playlist info."""
    return PlaylistInfo(
        playlist_id="OLAK5uy_test123",
        title="Test Album",
        cover_url="https://example.com/album.jpg",
        kind=ContentKind.ALBUM,
    )


@pytest.fixture
def sample_track() -> TrackMetadata:
    """Create a sample track."""
    return TrackMetadata(
        omv_video_id="omv123",
        atv_video_id="atv123",
        title="Test Song",
        artists=["Test Artist"],
        album="Test Album",
        album_artists=["Test Artist"],
        track_number=1,
        total_tracks=10,
        year="2024",
        cover_url="https://example.com/track.jpg",
        video_type=VideoType.ATV,
    )


@pytest.fixture
def download_results(
    sample_track: TrackMetadata, tmp_path: Path
) -> list[DownloadResult]:
    """Create sample download results."""
    track_path = tmp_path / "Artist" / "2024 - Album" / "01 - Song.opus"
    track_path.parent.mkdir(parents=True, exist_ok=True)
    track_path.touch()

    return [
        DownloadResult(
            track=sample_track,
            status=DownloadStatus.SUCCESS,
            output_path=track_path,
            video_id_used="atv123",
        ),
    ]


class TestPlaylistArtifactsService:
    """Tests for PlaylistArtifactsService."""

    @patch("yubal.services.artifacts.write_m3u")
    @patch("yubal.services.artifacts.write_playlist_cover")
    def test_compose_generates_m3u_and_cover(
        self,
        mock_cover: MagicMock,
        mock_m3u: MagicMock,
        composer: PlaylistArtifactsService,
        playlist_info: PlaylistInfo,
        download_results: list[DownloadResult],
        tmp_path: Path,
    ) -> None:
        """Should generate both M3U and cover files."""
        mock_m3u.return_value = tmp_path / "Playlists" / "Test Playlist.m3u"
        mock_cover.return_value = tmp_path / "Playlists" / "Test Playlist.jpg"

        m3u_path, cover_path = composer.compose(
            tmp_path, playlist_info, download_results
        )

        assert m3u_path == tmp_path / "Playlists" / "Test Playlist.m3u"
        assert cover_path == tmp_path / "Playlists" / "Test Playlist.jpg"
        mock_m3u.assert_called_once()
        mock_cover.assert_called_once()

    @patch("yubal.services.artifacts.write_m3u")
    @patch("yubal.services.artifacts.write_playlist_cover")
    def test_compose_skips_m3u_when_disabled(
        self,
        mock_cover: MagicMock,
        mock_m3u: MagicMock,
        composer: PlaylistArtifactsService,
        playlist_info: PlaylistInfo,
        download_results: list[DownloadResult],
        tmp_path: Path,
    ) -> None:
        """Should skip M3U generation when disabled."""
        mock_cover.return_value = tmp_path / "Playlists" / "Test Playlist.jpg"

        m3u_path, cover_path = composer.compose(
            tmp_path, playlist_info, download_results, generate_m3u=False
        )

        assert m3u_path is None
        assert cover_path is not None
        mock_m3u.assert_not_called()
        mock_cover.assert_called_once()

    @patch("yubal.services.artifacts.write_m3u")
    @patch("yubal.services.artifacts.write_playlist_cover")
    def test_compose_skips_cover_when_disabled(
        self,
        mock_cover: MagicMock,
        mock_m3u: MagicMock,
        composer: PlaylistArtifactsService,
        playlist_info: PlaylistInfo,
        download_results: list[DownloadResult],
        tmp_path: Path,
    ) -> None:
        """Should skip cover when disabled."""
        mock_m3u.return_value = tmp_path / "Playlists" / "Test Playlist.m3u"

        m3u_path, cover_path = composer.compose(
            tmp_path, playlist_info, download_results, save_cover=False
        )

        assert m3u_path is not None
        assert cover_path is None
        mock_m3u.assert_called_once()
        mock_cover.assert_not_called()

    @patch("yubal.services.artifacts.write_m3u")
    @patch("yubal.services.artifacts.write_playlist_cover")
    def test_compose_skips_m3u_for_album_playlist(
        self,
        mock_cover: MagicMock,
        mock_m3u: MagicMock,
        composer: PlaylistArtifactsService,
        album_playlist_info: PlaylistInfo,
        download_results: list[DownloadResult],
        tmp_path: Path,
    ) -> None:
        """Should skip M3U for album playlists when configured."""
        mock_cover.return_value = tmp_path / "Playlists" / "Test Album.jpg"

        m3u_path, cover_path = composer.compose(
            tmp_path, album_playlist_info, download_results, skip_album_m3u=True
        )

        assert m3u_path is None
        assert cover_path is not None
        mock_m3u.assert_not_called()

    @patch("yubal.services.artifacts.write_m3u")
    @patch("yubal.services.artifacts.write_playlist_cover")
    def test_compose_generates_m3u_for_album_when_not_skipping(
        self,
        mock_cover: MagicMock,
        mock_m3u: MagicMock,
        composer: PlaylistArtifactsService,
        album_playlist_info: PlaylistInfo,
        download_results: list[DownloadResult],
        tmp_path: Path,
    ) -> None:
        """Should generate M3U for album playlists when skip_album_m3u=False."""
        mock_m3u.return_value = tmp_path / "Playlists" / "Test Album.m3u"
        mock_cover.return_value = tmp_path / "Playlists" / "Test Album.jpg"

        m3u_path, _ = composer.compose(
            tmp_path, album_playlist_info, download_results, skip_album_m3u=False
        )

        assert m3u_path is not None
        mock_m3u.assert_called_once()

    def test_collect_tracks_filters_successful(
        self,
        composer: PlaylistArtifactsService,
        sample_track: TrackMetadata,
        tmp_path: Path,
    ) -> None:
        """Should only collect successful and skipped downloads."""
        track_path = tmp_path / "track.opus"
        track_path.touch()

        results = [
            DownloadResult(
                track=sample_track,
                status=DownloadStatus.SUCCESS,
                output_path=track_path,
            ),
            DownloadResult(
                track=sample_track,
                status=DownloadStatus.SKIPPED,
                output_path=track_path,
            ),
            DownloadResult(
                track=sample_track,
                status=DownloadStatus.FAILED,
                error="Test error",
            ),
        ]

        tracks = composer._collect_successful_tracks_for_playlist(results)

        # Should only include SUCCESS and SKIPPED (2 items)
        assert len(tracks) == 2

    def test_collect_tracks_excludes_missing_paths(
        self,
        composer: PlaylistArtifactsService,
        sample_track: TrackMetadata,
    ) -> None:
        """Should exclude results without output paths."""
        results = [
            DownloadResult(
                track=sample_track,
                status=DownloadStatus.SUCCESS,
                output_path=None,  # Missing path
            ),
        ]

        tracks = composer._collect_successful_tracks_for_playlist(results)

        assert len(tracks) == 0
