"""Cancellation token for async operations."""

import threading


class CancelToken:
    """Thread-safe cancellation token using threading.Event.

    Tokens are single-use - once cancelled, create a new token for the
    next operation.

    Example:
        >>> token = CancelToken()
        >>> # In worker thread:
        >>> if token.is_cancelled:
        ...     return  # Early exit
        >>> # In main thread:
        >>> token.cancel()  # Signal cancellation
    """

    __slots__ = ("_event",)

    def __init__(self) -> None:
        """Initialize a new cancellation token (not cancelled)."""
        self._event = threading.Event()

    def cancel(self) -> None:
        """Signal that the operation should be cancelled.

        Thread-safe. Can be called from any thread.
        """
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested.

        Thread-safe. Returns True if cancel() has been called.
        """
        return self._event.is_set()
