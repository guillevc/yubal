"""Tests for download service."""

import logging
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from yubal.config import AudioCodec, DownloadConfig
from yubal.exceptions import DownloadError
from yubal.models.enums import VideoType
from yubal.models.track import TrackMetadata
from yubal.services.downloader import (
    DownloadResult,
    DownloadService,
    DownloadStatus,
    YTDLPDownloader,
)


@pytest.fixture
def sample_track() -> TrackMetadata:
    """Create a sample track for testing."""
    return TrackMetadata(
        omv_video_id="omv123",
        atv_video_id="atv456",
        title="Test Song",
        artists=["Test Artist"],
        album="Test Album",
        album_artists=["Test Artist"],
        track_number=5,
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
        artists=["Another Artist"],
        album="Another Album",
        album_artists=["Another Artist"],
        track_number=1,
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

    def download(self, video_id: str, output_path: Path) -> Path:
        """Mock download that records calls and returns actual path."""
        self.downloads.append((video_id, output_path))
        if self.should_fail:
            raise DownloadError(f"Mock download failed for {video_id}")
        # Create an empty file to simulate download
        output_path.parent.mkdir(parents=True, exist_ok=True)
        actual_path = output_path.with_suffix(".opus")
        actual_path.touch()
        return actual_path


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

        progress_list = list(
            service.download_tracks([sample_track, sample_track_no_atv])
        )

        assert len(progress_list) == 2
        assert all(
            p.result is not None and p.result.status == DownloadStatus.SUCCESS
            for p in progress_list
        )
        assert len(mock_downloader.downloads) == 2

    def test_download_tracks_yields_progress(
        self,
        sample_track: TrackMetadata,
        sample_track_no_atv: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Should yield progress updates for each track."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        progress_list = list(
            service.download_tracks([sample_track, sample_track_no_atv])
        )

        assert len(progress_list) == 2
        assert progress_list[0].current == 1
        assert progress_list[0].total == 2
        assert progress_list[1].current == 2
        assert progress_list[1].total == 2
        assert progress_list[0].result is not None
        assert progress_list[1].result is not None

    def test_download_progress_model_is_frozen(
        self,
        sample_track: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """DownloadProgress should be immutable."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        progress_list = list(service.download_tracks([sample_track]))

        with pytest.raises(ValidationError):
            progress_list[0].current = 999

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

            def download(self, video_id: str, output_path: Path) -> Path:
                self.downloads.append(video_id)
                if video_id == "atv456":
                    raise DownloadError(f"Failed: {video_id}")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                actual_path = output_path.with_suffix(".opus")
                actual_path.touch()
                return actual_path

        downloader = SelectiveFailDownloader()
        service = DownloadService(download_config, downloader)

        progress_list = list(
            service.download_tracks([sample_track, sample_track_no_atv])
        )

        assert len(progress_list) == 2
        assert progress_list[0].result is not None
        assert progress_list[0].result.status == DownloadStatus.FAILED
        assert progress_list[1].result is not None
        assert progress_list[1].result.status == DownloadStatus.SUCCESS
        assert len(downloader.downloads) == 2  # Both were attempted

    def test_tagging_error_does_not_fail_download(
        self,
        sample_track: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Tagging errors should not cause download to fail."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        with patch(
            "yubal.services.downloader.tag_track",
            side_effect=Exception("Tagging failed"),
        ):
            result = service.download_track(sample_track)

        # Download should still succeed despite tagging error
        assert result.status == DownloadStatus.SUCCESS
        assert result.output_path is not None

    def test_skipped_files_not_tagged(
        self,
        sample_track: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Skipped files should not be tagged."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        # First download
        service.download_track(sample_track)

        with patch("yubal.services.downloader.tag_track") as mock_tag:
            # Second call should skip - no tagging
            result = service.download_track(sample_track)

        assert result.status == DownloadStatus.SKIPPED
        mock_tag.assert_not_called()

    def test_tagging_called_on_success(
        self,
        sample_track: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Tagging should be called after successful download."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        with (
            patch("yubal.services.downloader.tag_track") as mock_tag,
            patch("yubal.services.downloader.fetch_cover", return_value=b"cover data"),
        ):
            result = service.download_track(sample_track)

        assert result.status == DownloadStatus.SUCCESS
        mock_tag.assert_called_once()
        # Verify cover was passed to tag_track
        call_args = mock_tag.call_args[0]
        assert call_args[1] == sample_track  # track metadata
        assert call_args[2] == b"cover data"  # cover bytes


class TestDownloadResult:
    """Tests for DownloadResult model."""

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

        with pytest.raises(ValidationError):
            result.status = DownloadStatus.FAILED


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


class TestYTDLPDownloaderRetry:
    """Tests for YTDLPDownloader retry behavior."""

    def test_retry_on_403_with_eventual_success(
        self, download_config: DownloadConfig, tmp_path: Path
    ) -> None:
        """Should retry on 403 errors and succeed after transient failure."""
        downloader = YTDLPDownloader(download_config)
        output_path = tmp_path / "test_track"
        call_count = 0

        def mock_download(urls: list[str]) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("HTTP Error 403: Forbidden")
            # Success on third attempt - create the file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            Path(f"{output_path}.opus").touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl:
            mock_instance = mock_ydl.return_value.__enter__.return_value
            mock_instance.download = mock_download

            with patch("time.sleep"):  # Don't actually sleep in tests
                result = downloader.download("test_video_id", output_path)

        assert call_count == 3
        assert result.exists()

    def test_failure_after_max_retries(
        self, download_config: DownloadConfig, tmp_path: Path
    ) -> None:
        """Should fail after exhausting all retry attempts."""
        downloader = YTDLPDownloader(download_config)
        output_path = tmp_path / "test_track"
        call_count = 0

        def mock_download(urls: list[str]) -> None:
            nonlocal call_count
            call_count += 1
            raise Exception("HTTP Error 403: Forbidden")

        with patch("yt_dlp.YoutubeDL") as mock_ydl:
            mock_instance = mock_ydl.return_value.__enter__.return_value
            mock_instance.download = mock_download

            with patch("time.sleep"):
                with pytest.raises(DownloadError) as exc_info:
                    downloader.download("test_video_id", output_path)

        assert call_count == 4  # Initial + 3 retries
        assert "after 4 attempts" in str(exc_info.value)

    def test_no_retry_for_video_unavailable(
        self, download_config: DownloadConfig, tmp_path: Path
    ) -> None:
        """Should not retry for non-retryable errors like 'Video unavailable'."""
        downloader = YTDLPDownloader(download_config)
        output_path = tmp_path / "test_track"
        call_count = 0

        def mock_download(urls: list[str]) -> None:
            nonlocal call_count
            call_count += 1
            raise Exception("Video unavailable")

        with patch("yt_dlp.YoutubeDL") as mock_ydl:
            mock_instance = mock_ydl.return_value.__enter__.return_value
            mock_instance.download = mock_download

            with pytest.raises(DownloadError) as exc_info:
                downloader.download("test_video_id", output_path)

        assert call_count == 1  # No retries
        assert "unavailable" in str(exc_info.value)

    def test_warning_logs_on_retry(
        self,
        download_config: DownloadConfig,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Should log warnings on each retry attempt."""
        downloader = YTDLPDownloader(download_config)
        output_path = tmp_path / "test_track"
        call_count = 0

        def mock_download(urls: list[str]) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("HTTP Error 403: Forbidden")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            Path(f"{output_path}.opus").touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl:
            mock_instance = mock_ydl.return_value.__enter__.return_value
            mock_instance.download = mock_download

            with patch("time.sleep"):
                with caplog.at_level(logging.WARNING):
                    downloader.download("test_video_id", output_path)

        # Check that retry warnings were logged
        warning_messages = [
            r.message for r in caplog.records if r.levelno == logging.WARNING
        ]
        assert len(warning_messages) == 2  # Two retries before success
        assert all("Transient error" in msg for msg in warning_messages)
        assert "attempt 1/4" in warning_messages[0]
        assert "attempt 2/4" in warning_messages[1]

    def test_retry_on_429_rate_limit(
        self, download_config: DownloadConfig, tmp_path: Path
    ) -> None:
        """Should retry on 429 rate limit errors."""
        downloader = YTDLPDownloader(download_config)
        output_path = tmp_path / "test_track"
        call_count = 0

        def mock_download(urls: list[str]) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("HTTP Error 429: Too Many Requests")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            Path(f"{output_path}.opus").touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl:
            mock_instance = mock_ydl.return_value.__enter__.return_value
            mock_instance.download = mock_download

            with patch("time.sleep"):
                result = downloader.download("test_video_id", output_path)

        assert call_count == 2
        assert result.exists()

    def test_retry_on_5xx_server_error(
        self, download_config: DownloadConfig, tmp_path: Path
    ) -> None:
        """Should retry on 5xx server errors."""
        downloader = YTDLPDownloader(download_config)
        output_path = tmp_path / "test_track"
        call_count = 0

        def mock_download(urls: list[str]) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("HTTP Error 503: Service Unavailable")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            Path(f"{output_path}.opus").touch()

        with patch("yt_dlp.YoutubeDL") as mock_ydl:
            mock_instance = mock_ydl.return_value.__enter__.return_value
            mock_instance.download = mock_download

            with patch("time.sleep"):
                result = downloader.download("test_video_id", output_path)

        assert call_count == 2
        assert result.exists()
