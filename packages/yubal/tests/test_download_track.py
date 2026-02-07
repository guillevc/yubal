"""Tests for single track download support."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from yubal.config import DownloadConfig, PlaylistDownloadConfig
from yubal.models.enums import ContentKind, DownloadStatus, VideoType
from yubal.models.progress import DownloadProgress, ExtractProgress
from yubal.models.results import DownloadResult
from yubal.models.track import PlaylistInfo, TrackMetadata
from yubal.services.artifacts import ArtifactPaths
from yubal.services.pipeline import PlaylistDownloadService


@pytest.fixture
def single_track_metadata() -> TrackMetadata:
    """Single track metadata."""
    return TrackMetadata(
        atv_video_id="Vgpv5PtWsn4",
        omv_video_id=None,
        title="A COLD PLAY",
        artists=["The Kid LAROI"],
        album="A COLD PLAY",
        album_artists=["The Kid LAROI"],
        track_number=1,
        total_tracks=1,
        year="2025",
        cover_url="https://example.com/cover.jpg",
        video_type=VideoType.ATV,
    )


@pytest.fixture
def single_track_playlist_info() -> PlaylistInfo:
    """Playlist info for single track."""
    return PlaylistInfo(
        playlist_id="Vgpv5PtWsn4",
        title="A COLD PLAY",
        cover_url="https://example.com/cover.jpg",
        kind=ContentKind.TRACK,
    )


class TestDownloadTrack:
    """Tests for downloading single tracks via unified extract() API."""

    def test_download_single_track_url(
        self,
        single_track_metadata: TrackMetadata,
        single_track_playlist_info: PlaylistInfo,
        tmp_path: Path,
    ) -> None:
        """Should download a single track from a watch URL via extract()."""
        config = PlaylistDownloadConfig(
            download=DownloadConfig(base_path=tmp_path),
            generate_m3u=False,
            save_cover=False,
        )

        # Create ExtractProgress that extract() would yield for single track
        extract_progress = ExtractProgress(
            current=1,
            total=1,
            playlist_total=1,
            skipped_by_reason={},
            track=single_track_metadata,
            playlist_info=single_track_playlist_info,
        )

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = iter([extract_progress])

        mock_downloader = MagicMock()
        download_result = DownloadResult(
            track=single_track_metadata,
            status=DownloadStatus.SUCCESS,
            output_path=tmp_path / "test.opus",
        )
        download_progress = DownloadProgress(
            current=1,
            total=1,
            result=download_result,
        )
        mock_downloader.download_tracks.return_value = iter([download_progress])

        mock_composer = MagicMock()
        mock_composer.compose.return_value = ArtifactPaths()

        service = PlaylistDownloadService(
            config=config,
            extractor=mock_extractor,
            downloader=mock_downloader,
            composer=mock_composer,
        )

        # Consume the generator
        list(service.download_playlist("https://music.youtube.com/watch?v=Vgpv5PtWsn4"))

        # Verify extract() was called (unified API for all URL types)
        mock_extractor.extract.assert_called_once()

        # Verify download was called with the track
        mock_downloader.download_tracks.assert_called_once()

    def test_playlist_url_uses_extract(self, tmp_path: Path) -> None:
        """Should use extract() for playlist URLs."""
        config = PlaylistDownloadConfig(
            download=DownloadConfig(base_path=tmp_path),
            generate_m3u=False,
            save_cover=False,
        )

        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = iter([])  # Empty playlist

        service = PlaylistDownloadService(
            config=config,
            extractor=mock_extractor,
        )

        # Consume the generator
        list(
            service.download_playlist(
                "https://music.youtube.com/playlist?list=PLtest123"
            )
        )

        # Verify extract() was called (unified API for all URL types)
        mock_extractor.extract.assert_called_once()
