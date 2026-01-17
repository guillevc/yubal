"""Custom exceptions and error handlers for the API.

All API errors use a consistent response format:
{
    "error": "error_code",
    "message": "Human-readable description",
    ...additional context fields
}
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: str
    message: str


# -- Base Exceptions --


class YubalError(Exception):
    """Base exception for Yubal application errors.

    Subclasses should define:
    - status_code: HTTP status code
    - error_code: Machine-readable error identifier
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


# -- Job Exceptions --


class JobNotFoundError(YubalError):
    """Raised when a job is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "job_not_found"

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"Job {job_id} not found")


class JobConflictError(YubalError):
    """Raised when a job operation conflicts with existing state."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "job_conflict"

    def __init__(self, message: str, job_id: str | None = None) -> None:
        self.job_id = job_id
        super().__init__(message)


class QueueFullError(YubalError):
    """Raised when the job queue is at capacity."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "queue_full"

    def __init__(self) -> None:
        super().__init__("Job queue is full. Wait for existing jobs to complete.")


# -- Sync Operation Exceptions --


class DownloadError(YubalError):
    """Raised when a download operation fails."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "download_failed"


class CookieValidationError(YubalError):
    """Raised when cookie file validation fails."""

    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "invalid_cookies"


# -- Exception Handlers --


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI app."""

    @app.exception_handler(YubalError)
    async def yubal_error_handler(request: Request, exc: YubalError) -> JSONResponse:
        """Generic handler for all YubalError subclasses."""
        content: dict[str, str | None] = {
            "error": exc.error_code,
            "message": exc.message,
        }

        # Add job_id context if available
        job_id = getattr(exc, "job_id", None)
        if job_id is not None:
            content["job_id"] = job_id

        return JSONResponse(status_code=exc.status_code, content=content)
