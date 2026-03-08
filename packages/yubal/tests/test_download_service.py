"""Tests for download service."""

import logging
from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError
from yubal.config import AudioCodec, DownloadConfig
from yubal.exceptions import CancellationError, DownloadError
from yubal.models.cancel import CancelToken
from yubal.models.enums import MatchResult, VideoType
from yubal.models.track import TrackMetadata
from yubal.services.download_service import (
    DownloadResult,
    DownloadService,
    DownloadStatus,
    YTDLPDownloader,
)


@pytest.fixture(autouse=True)
def _mock_network_calls() -> Iterator[None]:
    """Mock network calls to avoid slow HTTP requests in tests."""
    with (
        patch(
            "yubal.services.download_service.fetch_cover", return_value=b"fake cover"
        ),
        patch(
            "yubal.services.lyrics.httpx.get", return_value=MagicMock(status_code=404)
        ),
    ):
        yield


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

    def download(
        self,
        video_id: str,
        output_path: Path,
        cancel_token: CancelToken | None = None,
    ) -> Path:
        """Mock download that records calls and returns actual path."""
        self.downloads.append((video_id, output_path))
        if self.should_fail:
            raise DownloadError(f"Mock download failed for {video_id}")
        if cancel_token and cancel_token.is_cancelled:
            raise CancellationError("Download cancelled")
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

            def download(
                self,
                video_id: str,
                output_path: Path,
                cancel_token: CancelToken | None = None,
            ) -> Path:
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

        with patch.object(
            service._tagger,
            "apply_metadata_tags",
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

        with patch.object(service._tagger, "apply_metadata_tags") as mock_tag:
            # Second call should skip - no tagging
            result = service.download_track(sample_track)

        assert result.status == DownloadStatus.SKIPPED
        mock_tag.assert_not_called()

    def test_download_unmatched_track_routes_to_unmatched_folder(
        self,
        download_config: DownloadConfig,
        tmp_path: Path,
    ) -> None:
        """Should route unmatched tracks to _Unmatched/ folder."""
        track = TrackMetadata(
            source_video_id="omv123",
            omv_video_id="omv123",
            atv_video_id=None,
            title="Mercury Retrograde",
            artists=["Wiz Khalifa"],
            album="Mercury Retrograde",
            album_artists=["Wiz Khalifa"],
            match_result=MatchResult.UNMATCHED,
        )
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        result = service.download_track(track)

        assert result.status == DownloadStatus.SUCCESS
        _, output_path = mock_downloader.downloads[0]
        assert "_Unmatched" in str(output_path)
        assert "Wiz Khalifa - Mercury Retrograde [omv123]" in str(output_path)

    def test_download_unofficial_track_routes_to_unofficial_folder(
        self,
        download_config: DownloadConfig,
        tmp_path: Path,
    ) -> None:
        """Should route unofficial (UGC) tracks to _Unofficial/ folder."""
        track = TrackMetadata(
            source_video_id="ugc123",
            omv_video_id=None,
            atv_video_id=None,
            title="User Upload",
            artists=["Some User"],
            album="User Upload",
            album_artists=["Some User"],
            video_type=VideoType.UGC,
            match_result=MatchResult.UNOFFICIAL,
        )
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        result = service.download_track(track)

        assert result.status == DownloadStatus.SUCCESS
        _, output_path = mock_downloader.downloads[0]
        assert "_Unofficial" in str(output_path)
        assert "Some User - User Upload [ugc123]" in str(output_path)

    def test_track_metadata_match_result_defaults_to_matched(
        self,
        sample_track: TrackMetadata,
    ) -> None:
        """TrackMetadata.match_result should default to MATCHED."""
        assert sample_track.match_result == MatchResult.MATCHED

    def test_tagging_called_on_success(
        self,
        sample_track: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Tagging should be called after successful download."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)

        with (
            patch.object(service._tagger, "apply_metadata_tags") as mock_tag,
            patch(
                "yubal.services.download_service.fetch_cover",
                return_value=b"cover data",
            ),
        ):
            result = service.download_track(sample_track)

        assert result.status == DownloadStatus.SUCCESS
        mock_tag.assert_called_once()
        # Verify cover was passed to apply_metadata_tags
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


class TestCancellation:
    """Tests for cancellation during downloads."""

    def test_download_tracks_cancels_between_tracks(
        self,
        sample_track: TrackMetadata,
        sample_track_no_atv: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """Should raise CancellationError when token is cancelled between tracks."""
        mock_downloader = MockDownloader()
        service = DownloadService(download_config, mock_downloader)
        token = CancelToken()

        # Cancel after first track downloads
        results = []
        with pytest.raises(CancellationError):
            for progress in service.download_tracks(
                [sample_track, sample_track_no_atv], cancel_token=token
            ):
                results.append(progress)
                token.cancel()  # Cancel after first track

        # First track downloaded, second was cancelled before starting
        assert len(results) == 1
        assert results[0].result.status == DownloadStatus.SUCCESS

    def test_download_track_cancels_mid_download(
        self,
        sample_track: TrackMetadata,
        download_config: DownloadConfig,
    ) -> None:
        """CancellationError when cancelled mid-download via hook."""

        class CancellingDownloader:
            """Downloader that simulates cancellation during download."""

            def download(
                self,
                video_id: str,
                output_path: Path,
                cancel_token: CancelToken | None = None,
            ) -> Path:
                if cancel_token and cancel_token.is_cancelled:
                    raise CancellationError("Download cancelled")
                output_path.parent.mkdir(parents=True, exist_ok=True)
                return output_path.with_suffix(".opus")

        service = DownloadService(download_config, CancellingDownloader())
        token = CancelToken()
        token.cancel()

        with pytest.raises(CancellationError):
            service.download_track(sample_track, cancel_token=token)

    def test_ytdlp_downloader_raises_cancellation_error(
        self, download_config: DownloadConfig, tmp_path: Path
    ) -> None:
        """YTDLPDownloader should raise CancellationError when token is cancelled."""
        from yt_dlp.utils import DownloadCancelled

        downloader = YTDLPDownloader(download_config)
        output_path = tmp_path / "test_track"
        token = CancelToken()
        token.cancel()

        def mock_download(urls: list[str]) -> None:
            # Simulate yt-dlp calling the progress hook which checks the token
            raise DownloadCancelled("Download cancelled")

        with patch("yt_dlp.YoutubeDL") as mock_ydl:
            mock_instance = mock_ydl.return_value.__enter__.return_value
            mock_instance.download = mock_download

            with pytest.raises(CancellationError, match="Download cancelled"):
                downloader.download("test_video_id", output_path, cancel_token=token)

    def test_ytdlp_downloader_cancel_hook_triggers_during_download(
        self, download_config: DownloadConfig, tmp_path: Path
    ) -> None:
        """Progress hook should raise DownloadCancelled when token is cancelled."""
        downloader = YTDLPDownloader(download_config)
        output_path = tmp_path / "test_track"
        token = CancelToken()

        captured_hooks: list[list] = []

        def mock_download(urls: list[str]) -> None:
            # yt-dlp would call progress hooks during download; simulate that
            for hook in captured_hooks[0]:
                token.cancel()  # Cancel mid-download
                hook({"status": "downloading"})

        with patch("yt_dlp.YoutubeDL") as mock_ydl:
            # Capture the opts passed to YoutubeDL to get the registered hooks
            def capture_opts(opts: dict) -> MagicMock:
                captured_hooks.append(opts.get("progress_hooks", []))
                mock_instance = MagicMock()
                mock_instance.__enter__ = MagicMock(return_value=mock_instance)
                mock_instance.__exit__ = MagicMock(return_value=False)
                mock_instance.download = mock_download
                return mock_instance

            mock_ydl.side_effect = capture_opts

            with pytest.raises(CancellationError, match="Download cancelled"):
                downloader.download("test_video_id", output_path, cancel_token=token)
