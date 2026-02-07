"""Shutdown coordination for graceful termination.

Handles Ctrl+C (SIGINT) and SIGTERM signals by:
1. Cancelling all running jobs
2. Delegating cleanup to yubal package
3. Suppressing log output during shutdown to prevent post-prompt messages
"""

import threading

from yubal_api.services.job_executor import JobExecutor


class ShutdownCoordinator:
    """Coordinates graceful shutdown with cleanup.

    Thread-safe coordinator that cancels running jobs when shutdown
    is requested. Cleanup of partial downloads is delegated to yubal.
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
