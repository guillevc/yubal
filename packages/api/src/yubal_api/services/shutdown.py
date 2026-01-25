"""Shutdown coordination for graceful termination.

Handles Ctrl+C (SIGINT) and SIGTERM signals by:
1. Cancelling all running jobs
2. Cleaning up .part files from incomplete downloads
3. Suppressing log output during shutdown to prevent post-prompt messages
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yubal_api.services.job_executor import JobExecutor

logger = logging.getLogger(__name__)


class ShutdownCoordinator:
    """Coordinates graceful shutdown with cleanup.

    Thread-safe coordinator that cancels running jobs and cleans up
    partial downloads when shutdown is requested.
    """

    def __init__(self) -> None:
        self._shutting_down = threading.Event()
        self._job_executor: JobExecutor | None = None

    def set_job_executor(self, executor: JobExecutor) -> None:
        """Set the job executor for cancellation during shutdown."""
        self._job_executor = executor

    @property
    def is_shutting_down(self) -> bool:
        """Check if shutdown has been initiated."""
        return self._shutting_down.is_set()

    def begin_shutdown(self) -> int:
        """Begin shutdown sequence - cancel all running jobs.

        Returns:
            Number of jobs that were cancelled.
        """
        self._shutting_down.set()

        cancelled = 0
        if self._job_executor:
            cancelled = self._job_executor.cancel_all_jobs()

        return cancelled

    def cleanup_part_files(self, data_dir: Path) -> int:
        """Remove .part files from data directory.

        Uses the same pattern as yubal's _cleanup_partial_downloads.

        Args:
            data_dir: Base data directory to search for .part files.

        Returns:
            Number of .part files cleaned up.
        """
        cleaned = 0

        try:
            for part_file in data_dir.rglob("*.part"):
                try:
                    part_file.unlink(missing_ok=True)
                    cleaned += 1
                except OSError:
                    pass  # Best effort cleanup
        except OSError:
            pass  # Directory might not exist

        return cleaned
