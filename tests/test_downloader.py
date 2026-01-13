"""Tests for download service."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from ytmeta.config import AudioCodec, DownloadConfig
from ytmeta.exceptions import DownloadError
from ytmeta.models.domain import TrackMetadata, VideoType
from ytmeta.services.downloader import (
    DownloadResult,
    DownloadService,
    DownloadStatus,
)


@pytest.fixture
def sample_track() -> TrackMetadata:
    """Create a sample track for testing."""
    return TrackMetadata(
        omv_video_id="omv123",
        atv_video_id="atv456",
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        albumartist="Test Artist",
        tracknumber=5,
        year="2024",
        cover_url="https://example.com/cover.jpg",
        video_type=VideoType.ATV,
    )


@pytest.fixture
def sample_track_no_atv() -> TrackMetadata:
    """Create a sample track without ATV video ID."""
    return TrackMetadata(
        omv_video_id="omv789",
        atv_video_id=None,
        title="Another Song",
        artist="Another Artist",
        album="Another Album",
        albumartist="Another Artist",
        tracknumber=1,
        year="2023",
        cover_url=None,
        video_type=VideoType.OMV,
    )


@pytest.fixture
def download_config(tmp_path: Path) -> DownloadConfig:
    """Create a download config with a temporary directory."""
    return DownloadConfig(
        base_path=tmp_path,
        codec=AudioCodec.OPUS,
        quality=0,
        quiet=True,
    )


class MockDownloader:
    """Mock downloader for testing."""

    def __init__(self, should_fail: bool = False) -> None:
        self.downloads: list[tuple[str, Path]] = []
        self.should_fail = should_fail

    def download(self, video_id: str, output_path: Path) -> None:
        """Mock download that records calls."""
        self.downloads.append((video_id, output_path))
        if self.should_fail:
            raise DownloadError(f"Mock download failed for {video_id}")
        # Create an empty file to simulate download
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.with_suffix(".opus").touch()


class TestDownloadService:
    """Tests for DownloadService."""

    def test_download_track_success(
        self,
        sample_track: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Should successfully download a track."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        result = service.download_track(sample_track)

        assert result.status == DownloadStatus.SUCCESS
        assert result.output_path is not None
        assert result.error is None
        assert result.video_id_used == "atv456"  # Should prefer ATV
        assert len(mock_downloader.downloads) == 1

    def test_download_track_prefers_atv(
        self,
        sample_track: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Should prefer ATV video ID when configured."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        service.download_track(sample_track)

        video_id, _ = mock_downloader.downloads[0]
        assert video_id == "atv456"

    def test_download_track_falls_back_to_omv(
        self,
        sample_track_no_atv: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Should fall back to OMV when ATV is not available."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        result = service.download_track(sample_track_no_atv)

        video_id, _ = mock_downloader.downloads[0]
        assert video_id == "omv789"
        assert result.video_id_used == "omv789"

    def test_download_track_failure(
        self,
        sample_track: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Should handle download failure gracefully."""
        mock_downloader = MockDownloader(should_fail=True)
        service = DownloadService(download_config, mock_downloader)

        result = service.download_track(sample_track)

        assert result.status == DownloadStatus.FAILED
        assert result.error is not None
        assert "Mock download failed" in result.error
        assert result.output_path is None

    def test_download_track_skips_existing(
        self,
        sample_track: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Should skip download when file already exists."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        # First download
        result1 = service.download_track(sample_track)
        assert result1.status == DownloadStatus.SUCCESS

        # Second download should be skipped
        result2 = service.download_track(sample_track)
        assert result2.status == DownloadStatus.SKIPPED
        assert result2.output_path is not None
        assert len(mock_downloader.downloads) == 1  # Only one actual download

    def test_download_track_builds_correct_path(
        self,
        sample_track: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Should build the correct output path structure."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        service.download_track(sample_track)

        _, output_path = mock_downloader.downloads[0]
        # Check path structure: base/Artist/YEAR - Album/NN - Title
        assert "Test Artist" in str(output_path)
        assert "2024 - Test Album" in str(output_path)
        assert "05 - Test Song" in str(output_path)

    def test_download_tracks_multiple(
        self,
        sample_track: TrackMetadata,
        sample_track_no_atv: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Should download multiple tracks."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        results = service.download_tracks([sample_track, sample_track_no_atv])

        assert len(results) == 2
        assert all(r.status == DownloadStatus.SUCCESS for r in results)
        assert len(mock_downloader.downloads) == 2

    def test_download_tracks_with_progress_callback(
        self,
        sample_track: TrackMetadata,
        sample_track_no_atv: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Should call progress callback for each track."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        progress_calls: list[tuple[int, int, DownloadResult]] = []

        def on_progress(current: int, total: int, result: DownloadResult) -> None:
            progress_calls.append((current, total, result))

        service.download_tracks(
            [sample_track, sample_track_no_atv],
            on_progress=on_progress,
        )

        assert len(progress_calls) == 2
        assert progress_calls[0][0] == 1  # current
        assert progress_calls[0][1] == 2  # total
        assert progress_calls[1][0] == 2

    def test_download_tracks_continues_on_failure(
        self,
        sample_track: TrackMetadata,
        sample_track_no_atv: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Should continue downloading after a failure."""

        class SelectiveFailDownloader:
            """Downloader that fails on specific video IDs."""

            def __init__(self) -> None:
                self.downloads: list[str] = []

            def download(self, video_id: str, output_path: Path) -> None:
                self.downloads.append(video_id)
                if video_id == "atv456":
                    raise DownloadError(f"Failed: {video_id}")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.with_suffix(".opus").touch()

        downloader = SelectiveFailDownloader()
        service = DownloadService(download_config, downloader)

        results = service.download_tracks([sample_track, sample_track_no_atv])

        assert len(results) == 2
        assert results[0].status == DownloadStatus.FAILED
        assert results[1].status == DownloadStatus.SUCCESS
        assert len(downloader.downloads) == 2  # Both were attempted


class TestDownloadResult:
    """Tests for DownloadResult dataclass."""

    def test_download_result_frozen(
        self,
        sample_track: TrackMetadata,
    ) -> None:
        """DownloadResult should be immutable."""
        result = DownloadResult(
            track=sample_track,
            status=DownloadStatus.SUCCESS,
            output_path=Path("/some/path.opus"),
        )

        with pytest.raises(FrozenInstanceError):
            result.status = DownloadStatus.FAILED  # type: ignore


class TestDownloadConfig:
    """Tests for DownloadConfig dataclass."""

    def test_download_config_defaults(self, tmp_path: Path) -> None:
        """Should have sensible defaults."""
        config = DownloadConfig(base_path=tmp_path)

        assert config.codec == AudioCodec.OPUS
        assert config.quality == 0
        assert config.quiet is True

    def test_download_config_frozen(self, tmp_path: Path) -> None:
        """DownloadConfig should be immutable."""
        config = DownloadConfig(base_path=tmp_path)

        with pytest.raises(FrozenInstanceError):
            config.codec = AudioCodec.MP3  # type: ignore
