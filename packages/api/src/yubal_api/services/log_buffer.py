"""Global log buffer for capturing and streaming structured JSON logs."""

import asyncio
import html
import logging
import threading
from collections import deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, ClassVar, override

from yubal_api.schemas.log import LogEntry, LogEntryType, LogStats


class LogBuffer:
    """Thread-safe global buffer for log lines with SSE subscription support.

    Captures structured log output and makes it available for streaming
    to clients via Server-Sent Events.

    Uses drop_oldest backpressure strategy: when a subscriber queue is full,
    the oldest message is dropped to make room for the new one.
    """

    MAX_LINES = 500
    SUBSCRIBER_QUEUE_SIZE = 100

    def __init__(self) -> None:
        self._lines: deque[str] = deque(maxlen=self.MAX_LINES)
        self._lock = threading.Lock()
        self._subscribers: list[asyncio.Queue[str]] = []
        self._subscribers_lock = threading.Lock()

    def append(self, line: str) -> None:
        """Append a line to the buffer and notify subscribers."""
        with self._lock:
            self._lines.append(line)

        # Notify SSE subscribers with drop_oldest backpressure
        with self._subscribers_lock:
            for queue in self._subscribers:
                try:
                    queue.put_nowait(line)
                except asyncio.QueueFull:
                    # Drop oldest message to make room for new one
                    try:
                        queue.get_nowait()
                        queue.put_nowait(line)
                    except asyncio.QueueEmpty:
                        pass  # Race condition, queue was drained

    def get_lines(self) -> list[str]:
        """Get all buffered lines."""
        with self._lock:
            return list(self._lines)

    def clear(self) -> None:
        """Clear all buffered lines."""
        with self._lock:
            self._lines.clear()

    @asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[str]]:
        """Subscribe to new log lines via context manager."""
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=self.SUBSCRIBER_QUEUE_SIZE)
        with self._subscribers_lock:
            self._subscribers.append(queue)
        try:
            yield queue
        finally:
            with self._subscribers_lock:
                self._subscribers.remove(queue)


class BufferHandler(logging.Handler):
    """Sends Pydantic-validated JSON logs for frontend rendering.

    The frontend is responsible for styling based on the structured data.
    This keeps the backend presentation-agnostic while ensuring type safety.

    Security: Messages are HTML-escaped to prevent XSS attacks.
    """

    EXTRA_FIELDS: ClassVar[list[str]] = [
        "phase",
        "phase_num",
        "event_type",
        "current",
        "total",
        "status",
        "file_path",
        "file_type",
        "track_title",
        "track_artist",
        "header",
    ]

    def __init__(self, buffer: LogBuffer) -> None:
        super().__init__()
        self._buffer = buffer

    @override
    def emit(self, record: logging.LogRecord) -> None:
        """Serialize log record to validated JSON and append to buffer."""
        try:
            entry_data: dict[str, Any] = {
                "timestamp": datetime.fromtimestamp(record.created).strftime(
                    "%H:%M:%S"
                ),
                "level": record.levelname,
                "message": html.escape(record.getMessage()),  # XSS prevention
            }

            # Add structured extras
            for field in self.EXTRA_FIELDS:
                if hasattr(record, field):
                    entry_data[field] = getattr(record, field)

            # Handle stats (convert dict to LogStats model)
            stats_value = getattr(record, "stats", None)
            if isinstance(stats_value, dict):
                entry_data["stats"] = LogStats(**stats_value)

            # Compute entry_type for frontend discriminated union
            entry_data["entry_type"] = self._compute_entry_type(entry_data)

            # Validate with Pydantic and serialize
            log_entry = LogEntry(**entry_data)
            self._buffer.append(log_entry.model_dump_json())
        except Exception:
            self.handleError(record)

    def _compute_entry_type(self, entry_data: dict[str, Any]) -> LogEntryType:
        """Determine entry type based on present fields for discriminated union."""
        if entry_data.get("header") is not None:
            return "header"
        if entry_data.get("phase") is not None:
            return "phase"
        if entry_data.get("stats") is not None:
            return "stats"
        if (
            entry_data.get("current") is not None
            and entry_data.get("total") is not None
        ):
            return "progress"
        if entry_data.get("status") is not None:
            return "status"
        if (
            entry_data.get("file_path") is not None
            or entry_data.get("file_type") is not None
        ):
            return "file"
        return "default"


# Global singleton
_log_buffer: LogBuffer | None = None


def get_log_buffer() -> LogBuffer:
    """Get the global log buffer singleton."""
    global _log_buffer
    if _log_buffer is None:
        _log_buffer = LogBuffer()
    return _log_buffer


def clear_log_buffer() -> None:
    """Clear the global log buffer singleton."""
    global _log_buffer
    _log_buffer = None
