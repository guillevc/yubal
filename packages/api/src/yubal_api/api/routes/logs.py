"""Log streaming endpoints."""

import asyncio
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from yubal_api.api.deps import LogBufferDep
from yubal_api.schemas.logs import LogEntry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["logs"])

# Heartbeat interval in seconds to prevent connection timeouts
HEARTBEAT_INTERVAL = 30


@router.get(
    "",
    summary="Get buffered log entries",
    description="Returns all currently buffered log entries as an array.",
)
async def get_logs(log_buffer: LogBufferDep) -> list[LogEntry]:
    """Get all buffered log entries.

    Returns the current log buffer contents. Useful for initial page load
    before connecting to the SSE stream.
    """
    buffer = log_buffer
    entries: list[LogEntry] = []
    for line in buffer.get_lines():
        try:
            entries.append(LogEntry.model_validate_json(line))
        except Exception:
            logger.debug("Skipping invalid log entry: %s", line[:100])
    return entries


@router.get(
    "/sse",
    response_class=StreamingResponse,
    summary="Stream log entries via SSE",
    description=(
        "On connect, sends all buffered log entries, "
        "then streams new entries as they arrive. "
        "Heartbeat comments sent every 30s."
    ),
)
async def stream_logs(log_buffer: LogBufferDep) -> StreamingResponse:
    """Stream structured log entries via Server-Sent Events."""
    buffer = log_buffer

    async def event_generator() -> AsyncIterator[str]:
        async with buffer.subscribe() as queue:
            # Send existing lines first
            for line in buffer.get_lines():
                yield f"data: {line}\n\n"

            # Stream new lines with heartbeat to prevent timeouts
            while True:
                try:
                    line = await asyncio.wait_for(
                        queue.get(), timeout=HEARTBEAT_INTERVAL
                    )
                    yield f"data: {line}\n\n"
                except TimeoutError:
                    # Send SSE comment as heartbeat
                    yield ": heartbeat\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
