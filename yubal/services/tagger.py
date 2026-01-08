import os
import subprocess
import sys
from pathlib import Path

from loguru import logger

from yubal.core.callbacks import ProgressCallback, ProgressEvent
from yubal.core.enums import ProgressStep
from yubal.core.models import TagResult

# Number of newlines to send to beets stdin to auto-accept prompts
_BEETS_STDIN_NEWLINES = 10
# Timeout for beets import operations in seconds
_BEETS_TIMEOUT_SECONDS = 300


class Tagger:
    """Handles music tagging and organization via beets CLI."""

    def __init__(self, beets_config: Path, library_dir: Path, beets_db: Path):
        self.beets_config = beets_config
        self.library_dir = library_dir
        self.beets_db = beets_db

    def _get_beet_command(self) -> list[str]:
        """Get the command to run beets using the current Python."""
        # Use python -m to avoid shebang issues with venv scripts
        return [sys.executable, "-m", "beets"]

    def _get_beets_env(self) -> dict[str, str]:
        """Get environment variables for running beets commands."""
        env = os.environ.copy()
        env["BEETSDIR"] = str(self.beets_config.parent)
        return env

    def _execute_beets_command(
        self,
        cmd: list[str],
        log_prefix: str = "",
        progress_callback: ProgressCallback | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """
        Execute a beets command with streaming output.

        Common execution logic shared by all beets import operations.

        Args:
            cmd: Complete command to execute
            log_prefix: Optional prefix for log messages (e.g., "(in-place)")
            progress_callback: Optional callback for progress updates

        Returns:
            CompletedProcess with stdout captured
        """
        # Ensure directories exist
        self.library_dir.mkdir(parents=True, exist_ok=True)
        self.beets_db.parent.mkdir(parents=True, exist_ok=True)

        prefix = f" {log_prefix}" if log_prefix else ""
        msg = f"Running beets{prefix}: {' '.join(cmd)}"
        logger.info(msg)
        if progress_callback:
            progress_callback(
                ProgressEvent(
                    step=ProgressStep.IMPORTING,
                    message=msg,
                )
            )

        # Use Popen to stream output in real-time
        # Pipe stdin with newlines to auto-accept prompts (beets -q needs stdin open)
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine stderr into stdout
            text=True,
            env=self._get_beets_env(),
            cwd=str(self.beets_config.parent.parent),
        )
        if process.stdin is None or process.stdout is None:
            raise RuntimeError("Process pipes not available")

        # Send newlines to accept any prompts, then close stdin
        process.stdin.write("\n" * _BEETS_STDIN_NEWLINES)
        process.stdin.close()

        stdout_lines = []
        for line in process.stdout:
            line = line.rstrip()
            if "error" in line.lower():
                logger.error("[beets] {}", line)
            else:
                logger.info("[beets] {}", line)
            if progress_callback:
                progress_callback(
                    ProgressEvent(
                        step=ProgressStep.IMPORTING,
                        message=f"[beets] {line}",
                    )
                )
            stdout_lines.append(line)

        process.wait(timeout=_BEETS_TIMEOUT_SECONDS)

        msg = f"Beets returncode: {process.returncode}"
        logger.info(msg)
        if progress_callback:
            progress_callback(
                ProgressEvent(
                    step=ProgressStep.IMPORTING,
                    message=msg,
                    details={"returncode": process.returncode},
                )
            )

        return subprocess.CompletedProcess(
            args=cmd,
            returncode=process.returncode,
            stdout="\n".join(stdout_lines),
            stderr="",
        )

    def tag_album(
        self,
        audio_files: list[Path],
        progress_callback: ProgressCallback | None = None,
    ) -> TagResult:
        """
        Tag and organize an album using beets.

        Moves files to the organized library structure.
        Import settings (quiet, move) are configured in beets config.yaml.

        Args:
            audio_files: List of audio file paths to import
            progress_callback: Optional callback for progress updates

        Returns:
            TagResult with success status and final location
        """
        if not audio_files:
            return TagResult(
                success=False,
                source_dir="",
                error="No audio files provided",
            )

        # All files should be in the same directory (temp dir from downloader)
        source_dir = audio_files[0].parent

        try:
            result = self._run_beets_import(
                source_dir, progress_callback=progress_callback
            )

            if result.returncode != 0:
                error_msg = f"Beets failed (code {result.returncode}): {result.stdout}"
                logger.error(error_msg)
                return TagResult(
                    success=False,
                    source_dir=str(source_dir),
                    error=error_msg,
                )

            # Find where the album was imported
            dest_dir = self._find_imported_album(source_dir)
            track_count = len(audio_files)

            return TagResult(
                success=True,
                source_dir=str(source_dir),
                dest_dir=str(dest_dir) if dest_dir else None,
                track_count=track_count,
            )

        except subprocess.TimeoutExpired:
            return TagResult(
                success=False,
                source_dir=str(source_dir),
                error=f"Beets timed out after {_BEETS_TIMEOUT_SECONDS // 60} minutes",
            )
        except FileNotFoundError as e:
            return TagResult(
                success=False,
                source_dir=str(source_dir),
                error=f"Beets module not found. Error: {e}",
            )
        except Exception as e:
            return TagResult(
                success=False,
                source_dir=str(source_dir),
                error=f"Unexpected error during tagging: {e!s}",
            )

    def _run_beets_import(
        self,
        source_dir: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """
        Execute beets import command for albums.

        Uses explicit flags for move behavior.
        """
        cmd = [
            *self._get_beet_command(),
            "--config",
            str(self.beets_config),
            "--directory",
            str(self.library_dir),
            "import",
            "-m",  # Move files into library directory
            str(source_dir),
        ]

        return self._execute_beets_command(cmd, progress_callback=progress_callback)

    def _find_imported_album(self, source_dir: Path) -> Path | None:
        """
        Find where beets moved the album in the library.

        Since beets organizes by artist/album, we look for recently
        modified directories in the library.
        """
        if not self.library_dir.exists():
            return None

        # Find the most recently modified album directory using generator
        album_dirs = (
            album_dir
            for artist_dir in self.library_dir.iterdir()
            if artist_dir.is_dir()
            for album_dir in artist_dir.iterdir()
            if album_dir.is_dir()
        )

        return max(album_dirs, key=lambda d: d.stat().st_mtime, default=None)

    def tag_playlist(
        self,
        audio_files: list[Path],
        progress_callback: ProgressCallback | None = None,
    ) -> TagResult:
        """
        Tag playlist files in place without moving them.

        Unlike tag_album which moves files to Artist/Album/ structure,
        this keeps files in their current location (Playlists/{name}/)
        and just enriches metadata via beets.

        Args:
            audio_files: List of audio file paths to import
            progress_callback: Optional callback for progress updates

        Returns:
            TagResult with success status (dest_dir = source_dir)
        """
        if not audio_files:
            return TagResult(
                success=False,
                source_dir="",
                error="No audio files provided",
            )

        source_dir = audio_files[0].parent

        try:
            result = self._run_beets_import_in_place(
                source_dir, progress_callback=progress_callback
            )

            if result.returncode != 0:
                error_msg = f"Beets failed (code {result.returncode}): {result.stdout}"
                logger.error(error_msg)
                return TagResult(
                    success=False,
                    source_dir=str(source_dir),
                    error=error_msg,
                )

            # For playlists, files stay in place - dest = source
            return TagResult(
                success=True,
                source_dir=str(source_dir),
                dest_dir=str(source_dir),
                track_count=len(audio_files),
            )

        except subprocess.TimeoutExpired:
            return TagResult(
                success=False,
                source_dir=str(source_dir),
                error=f"Beets timed out after {_BEETS_TIMEOUT_SECONDS // 60} minutes",
            )
        except FileNotFoundError as e:
            return TagResult(
                success=False,
                source_dir=str(source_dir),
                error=f"Beets module not found. Error: {e}",
            )
        except Exception as e:
            return TagResult(
                success=False,
                source_dir=str(source_dir),
                error=f"Unexpected error during tagging: {e!s}",
            )

    def _run_beets_import_in_place(
        self,
        source_dir: Path,
        progress_callback: ProgressCallback | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """
        Execute beets import keeping files in place.

        Used for playlists where we want MusicBrainz matching to enrich
        metadata, but files should stay in their Playlists/{name}/ location.
        """
        cmd = [
            *self._get_beet_command(),
            "--config",
            str(self.beets_config),
            "--directory",
            str(self.library_dir),
            "import",
            "-C",  # Don't copy files (keep in place)
            str(source_dir),
        ]

        return self._execute_beets_command(
            cmd, log_prefix="(in-place)", progress_callback=progress_callback
        )
