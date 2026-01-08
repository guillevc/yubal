"""Thread-safe cancellation token for sync operations."""

import threading


class CancelToken:
    """Thread-safe cancellation token using threading.Event.

    Provides a simple interface for signaling and checking cancellation
    across threads during long-running operations.

    Example:
        token = CancelToken()
        # In worker thread:
        if token.is_cancelled():
            return  # Early exit
        # In main thread:
        token.cancel()  # Signal cancellation
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

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested.

        Thread-safe. Returns True if cancel() has been called.
        """
        return self._event.is_set()

    def reset(self) -> None:
        """Reset the token to non-cancelled state.

        Useful for reusing tokens, though creating new ones is typically safer.
        """
        self._event.clear()
