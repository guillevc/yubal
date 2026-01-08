"""Progress reporting abstractions for sync operations."""

from typing import Protocol

from yubal.core.callbacks import ProgressCallback, ProgressEvent
from yubal.core.enums import ProgressStep


class ProgressEmitter(Protocol):
    """Protocol for emitting progress updates during sync operations.

    Provides a clean interface for services to report progress without
    being coupled to specific callback implementations.
    """

    def emit(
        self,
        step: ProgressStep,
        message: str,
        progress: float | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        """Emit a progress update.

        Args:
            step: Current workflow step
            message: Human-readable progress message
            progress: Optional percentage (0-100)
            details: Optional additional data (e.g., album_info)
        """
        ...

    def fail(self, message: str) -> None:
        """Emit a failure event.

        Args:
            message: Error message describing what failed
        """
        ...

    def complete(self, message: str, destination: str) -> None:
        """Emit a completion event.

        Args:
            message: Success message
            destination: Final output path/location
        """
        ...

    def create_download_wrapper(
        self,
        total_tracks: int,
        start_progress: float,
        end_progress: float,
    ) -> ProgressCallback | None:
        """Create a wrapper callback that maps track progress to overall progress.

        Args:
            total_tracks: Total number of tracks to download
            start_progress: Overall progress percentage at download start
            end_progress: Overall progress percentage at download end

        Returns:
            A ProgressCallback that scales individual track progress to the
            given range, or None if no callback is configured.
        """
        ...


class CallbackProgressEmitter:
    """ProgressEmitter implementation that wraps an existing ProgressCallback.

    Bridges the new ProgressEmitter protocol with the existing callback-based
    infrastructure used by routes and job management.

    Example:
        def my_callback(event: ProgressEvent) -> None:
            print(f"{event.step}: {event.message}")

        emitter = CallbackProgressEmitter(my_callback)
        emitter.emit(ProgressStep.DOWNLOADING, "Starting download...", progress=0.0)
    """

    __slots__ = ("_callback",)

    def __init__(self, callback: ProgressCallback | None = None) -> None:
        """Initialize the emitter with an optional callback.

        Args:
            callback: Optional callback function. If None, all emit calls are no-ops.
        """
        self._callback = callback

    def emit(
        self,
        step: ProgressStep,
        message: str,
        progress: float | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        """Emit a progress update via the wrapped callback."""
        if self._callback is None:
            return

        event_kwargs: dict[str, object] = {
            "step": step,
            "message": message,
        }
        if progress is not None:
            event_kwargs["progress"] = progress
        if details is not None:
            event_kwargs["details"] = details

        self._callback(ProgressEvent(**event_kwargs))  # type: ignore[arg-type]

    def fail(self, message: str) -> None:
        """Emit a failure event."""
        self.emit(ProgressStep.FAILED, message)

    def complete(self, message: str, destination: str) -> None:
        """Emit a completion event."""
        self.emit(
            ProgressStep.COMPLETED,
            f"Sync complete: {destination}",
            progress=100.0,
        )

    def create_download_wrapper(
        self,
        total_tracks: int,
        start_progress: float,
        end_progress: float,
    ) -> ProgressCallback | None:
        """Create a wrapper callback that maps track progress to overall progress.

        Args:
            total_tracks: Total number of tracks to download
            start_progress: Overall progress percentage at download start
            end_progress: Overall progress percentage at download end

        Returns:
            A ProgressCallback that scales individual track progress to the
            given range, or None if no callback is configured.
        """
        if self._callback is None:
            return None

        progress_range = end_progress - start_progress

        def wrapper(event: ProgressEvent) -> None:
            if event.progress is None:
                self._callback(event)  # type: ignore[misc]
                return

            track_idx = event.details.get("track_index", 0) if event.details else 0
            track_progress = event.progress

            overall = (
                start_progress
                + ((track_idx + track_progress / 100) / total_tracks) * progress_range
            )
            self._callback(  # type: ignore[misc]
                ProgressEvent(
                    step=ProgressStep.DOWNLOADING,
                    message=event.message,
                    progress=overall,
                )
            )

        return wrapper


class NullProgressEmitter:
    """No-op implementation of ProgressEmitter for testing or silent operations."""

    def emit(
        self,
        step: ProgressStep,
        message: str,
        progress: float | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        """Do nothing."""

    def fail(self, message: str) -> None:
        """Do nothing."""

    def complete(self, message: str, destination: str) -> None:
        """Do nothing."""

    def create_download_wrapper(
        self,
        total_tracks: int,
        start_progress: float,
        end_progress: float,
    ) -> ProgressCallback | None:
        """Return None (no callback)."""
        return None
