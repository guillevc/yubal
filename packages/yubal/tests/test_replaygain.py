"""Tests for ReplayGain service."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from yubal.config import AudioCodec
from yubal.services.replaygain import ReplayGainService


class TestReplayGainServiceAvailability:
    """Tests for rsgain availability checking."""

    def test_is_available_when_rsgain_installed(self) -> None:
        """Should return True when rsgain is in PATH."""
        service = ReplayGainService()
        with patch(
            "yubal.services.replaygain.shutil.which", return_value="/usr/bin/rsgain"
        ):
            assert service.is_available() is True

    def test_is_available_when_rsgain_not_installed(self) -> None:
        """Should return False when rsgain is not in PATH."""
        service = ReplayGainService()
        with patch("yubal.services.replaygain.shutil.which", return_value=None):
            assert service.is_available() is False


class TestReplayGainServiceApply:
    """Tests for applying ReplayGain tags."""

    @pytest.fixture
    def service(self) -> ReplayGainService:
        """Create a ReplayGainService instance."""
        return ReplayGainService()

    @pytest.fixture
    def mock_files(self, tmp_path: Path) -> list[Path]:
        """Create mock audio files."""
        files = [
            tmp_path / "01 - Track One.opus",
            tmp_path / "02 - Track Two.opus",
        ]
        for f in files:
            f.touch()
        return files

    def test_apply_replaygain_empty_files_returns_true(
        self, service: ReplayGainService
    ) -> None:
        """Should return True immediately for empty file list."""
        result = service.apply_replaygain([], AudioCodec.OPUS)
        assert result is True

    def test_apply_replaygain_rsgain_not_available(
        self, service: ReplayGainService, mock_files: list[Path]
    ) -> None:
        """Should return False and log warning when rsgain not available."""
        with patch.object(service, "is_available", return_value=False):
            result = service.apply_replaygain(mock_files, AudioCodec.OPUS)
            assert result is False

    def test_apply_replaygain_success(
        self, service: ReplayGainService, mock_files: list[Path]
    ) -> None:
        """Should return True when rsgain succeeds."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = ""

        with (
            patch.object(service, "is_available", return_value=True),
            patch("yubal.services.replaygain.subprocess.run", return_value=mock_result),
        ):
            result = service.apply_replaygain(mock_files, AudioCodec.OPUS)
            assert result is True

    def test_apply_replaygain_failure(
        self, service: ReplayGainService, mock_files: list[Path]
    ) -> None:
        """Should return False when rsgain fails."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error processing files"
        mock_result.stdout = ""

        with (
            patch.object(service, "is_available", return_value=True),
            patch("yubal.services.replaygain.subprocess.run", return_value=mock_result),
        ):
            result = service.apply_replaygain(mock_files, AudioCodec.OPUS)
            assert result is False

    def test_apply_replaygain_timeout(
        self, service: ReplayGainService, mock_files: list[Path]
    ) -> None:
        """Should return False when rsgain times out."""
        import subprocess

        with (
            patch.object(service, "is_available", return_value=True),
            patch(
                "yubal.services.replaygain.subprocess.run",
                side_effect=subprocess.TimeoutExpired("rsgain", 300),
            ),
        ):
            result = service.apply_replaygain(mock_files, AudioCodec.OPUS)
            assert result is False

    def test_apply_replaygain_os_error(
        self, service: ReplayGainService, mock_files: list[Path]
    ) -> None:
        """Should return False when rsgain cannot be executed."""
        with (
            patch.object(service, "is_available", return_value=True),
            patch(
                "yubal.services.replaygain.subprocess.run",
                side_effect=OSError("Permission denied"),
            ),
        ):
            result = service.apply_replaygain(mock_files, AudioCodec.OPUS)
            assert result is False

    def test_apply_replaygain_all_files_missing(
        self, service: ReplayGainService
    ) -> None:
        """Should return False when all files are missing."""
        missing_files = [
            Path("/nonexistent/track1.opus"),
            Path("/nonexistent/track2.opus"),
        ]
        with patch.object(service, "is_available", return_value=True):
            result = service.apply_replaygain(missing_files, AudioCodec.OPUS)
            assert result is False

    def test_apply_replaygain_partial_files_missing_falls_back_to_track_mode(
        self, service: ReplayGainService, mock_files: list[Path], tmp_path: Path
    ) -> None:
        """Should fall back to track-only mode when some files are missing."""
        # Add a non-existent file to the list
        files_with_missing = [*mock_files, tmp_path / "missing.opus"]

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_result.stdout = ""

        with (
            patch.object(service, "is_available", return_value=True),
            patch(
                "yubal.services.replaygain.subprocess.run", return_value=mock_result
            ) as mock_run,
        ):
            result = service.apply_replaygain(
                files_with_missing, AudioCodec.OPUS, album_mode=True
            )
            assert result is True
            # Verify album mode was disabled (no -a flag)
            cmd = mock_run.call_args[0][0]
            assert "-a" not in cmd
            # Verify only existing files were passed
            assert len([arg for arg in cmd if arg.endswith(".opus")]) == len(mock_files)


class TestReplayGainServiceCommandBuilding:
    """Tests for rsgain command construction."""

    @pytest.fixture
    def service(self) -> ReplayGainService:
        """Create a ReplayGainService instance."""
        return ReplayGainService()

    @pytest.fixture
    def files(self) -> list[Path]:
        """Create test file paths."""
        return [Path("/music/track1.opus"), Path("/music/track2.opus")]

    def test_build_command_album_mode_opus(
        self, service: ReplayGainService, files: list[Path]
    ) -> None:
        """Should build correct command for Opus album mode."""
        cmd = service._build_command(files, AudioCodec.OPUS, album_mode=True)

        assert cmd[0] == "rsgain"
        assert cmd[1] == "custom"
        assert "-s" in cmd
        assert cmd[cmd.index("-s") + 1] == "i"
        assert "-a" in cmd
        assert "-o" in cmd
        assert cmd[cmd.index("-o") + 1] == "r"
        assert str(files[0]) in cmd
        assert str(files[1]) in cmd

    def test_build_command_track_mode_opus(
        self, service: ReplayGainService, files: list[Path]
    ) -> None:
        """Should build correct command for Opus track-only mode."""
        cmd = service._build_command(files, AudioCodec.OPUS, album_mode=False)

        assert "rsgain" in cmd
        assert "-s" in cmd
        assert "-a" not in cmd
        assert "-o" in cmd

    def test_build_command_album_mode_mp3(
        self, service: ReplayGainService, files: list[Path]
    ) -> None:
        """Should build correct command for MP3 album mode (no -o flag)."""
        cmd = service._build_command(files, AudioCodec.MP3, album_mode=True)

        assert "rsgain" in cmd
        assert "-a" in cmd
        assert "-o" not in cmd  # No R128 flag for non-Opus

    def test_build_command_track_mode_m4a(
        self, service: ReplayGainService, files: list[Path]
    ) -> None:
        """Should build correct command for M4A track-only mode."""
        cmd = service._build_command(files, AudioCodec.M4A, album_mode=False)

        assert "rsgain" in cmd
        assert "-a" not in cmd
        assert "-o" not in cmd
