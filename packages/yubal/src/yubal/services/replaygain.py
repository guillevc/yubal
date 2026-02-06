"""ReplayGain tagging service using rsgain."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from yubal.config import AudioCodec

logger = logging.getLogger(__name__)

# Timeout for rsgain execution (5 minutes should be enough for most albums)
RSGAIN_TIMEOUT = 300


def _is_rsgain_available() -> bool:
    """Check if rsgain is available in PATH.

    Not cached since shutil.which is fast (<1ms) and users may install
    rsgain after starting the server.
    """
    return shutil.which("rsgain") is not None


class ReplayGainService:
    """Service for applying ReplayGain/R128 tags using rsgain.

    rsgain is a fast ReplayGain 2.0 scanner that supports all audio formats.
    For Opus files, it writes RFC 7845 compliant R128 tags (R128_TRACK_GAIN,
    R128_ALBUM_GAIN).

    This service is designed for post-processing freshly downloaded tracks.
    All errors are non-fatal - the service logs warnings and returns False
    on failure, allowing the download pipeline to continue.

    Example:
        >>> service = ReplayGainService()
        >>> if service.is_available():
        ...     success = service.apply_replaygain(files, AudioCodec.OPUS)
        ...     if success:
        ...         print("ReplayGain tags applied")
    """

    def is_available(self) -> bool:
        """Check if rsgain is available in PATH.

        Returns:
            True if rsgain is installed and accessible, False otherwise.
        """
        return _is_rsgain_available()

    def apply_replaygain(
        self,
        files: list[Path],
        codec: AudioCodec,
        *,
        album_mode: bool = True,
    ) -> bool:
        """Apply ReplayGain tags to audio files using rsgain.

        Runs rsgain to calculate and write loudness normalization tags.
        For Opus files, uses RFC 7845 compliant R128 tags.

        Args:
            files: List of audio file paths to process.
            codec: Audio codec of the files (affects tag format for Opus).
            album_mode: If True, calculate album gain in addition to track gain.
                       Use False for playlists or partial album downloads.

        Returns:
            True if rsgain completed successfully, False on any error.
            Errors are logged as warnings but do not raise exceptions.
        """
        if not files:
            logger.debug("No files to process for ReplayGain")
            return True

        if not self.is_available():
            logger.warning(
                "rsgain not found in PATH, skipping ReplayGain tagging. "
                "Install rsgain to enable loudness normalization."
            )
            return False

        # Validate files exist (may have been deleted between download and normalize)
        existing_files = [f for f in files if f.exists()]
        if not existing_files:
            logger.warning("No files found for ReplayGain tagging (all files missing)")
            return False

        # If any files missing in album mode, fall back to track-only
        # (album gain calculation would be wrong with partial files)
        if len(existing_files) < len(files) and album_mode:
            logger.warning(
                "Missing %d file(s), using track-only mode for ReplayGain",
                len(files) - len(existing_files),
            )
            album_mode = False

        cmd = self._build_command(existing_files, codec, album_mode=album_mode)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=RSGAIN_TIMEOUT,
                check=False,
            )

            if result.returncode != 0:
                logger.warning(
                    "rsgain failed with exit code %d: %s",
                    result.returncode,
                    result.stderr.strip() or result.stdout.strip(),
                )
                return False

            file_count = len(existing_files)
            mode_desc = "album + track" if album_mode else "track only"
            logger.debug(
                "Applied ReplayGain (%s) to %d file(s)",
                mode_desc,
                file_count,
            )
            return True

        except subprocess.TimeoutExpired:
            logger.warning(
                "rsgain timed out after %d seconds",
                RSGAIN_TIMEOUT,
            )
            return False
        except OSError as e:
            logger.warning("Failed to run rsgain: %s", e)
            return False

    def _build_command(
        self,
        files: list[Path],
        codec: AudioCodec,
        *,
        album_mode: bool,
    ) -> list[str]:
        """Build the rsgain command with appropriate flags.

        Args:
            files: List of audio file paths to process.
            codec: Audio codec of the files.
            album_mode: Whether to calculate album gain.

        Returns:
            Command list suitable for subprocess.run().
        """
        # Base command: rsgain custom -q -s i (quiet mode, scan and INSERT tags)
        cmd = ["rsgain", "custom", "-q", "-s", "i"]

        # Add album mode flag
        if album_mode:
            cmd.append("-a")

        # Use RFC 7845 R128 tags for Opus files
        if codec == AudioCodec.OPUS:
            cmd.extend(["-o", "r"])

        # Add file paths
        cmd.extend(str(f) for f in files)

        return cmd
