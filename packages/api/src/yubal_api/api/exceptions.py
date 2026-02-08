"""Custom exceptions and error handlers for the API.

All API errors use a consistent response format:
{
    "error": "error_code",
    "message": "Human-readable description",
    ...additional context fields
}
"""

from typing import Any
from uuid import UUID

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


# -- Subscription Exceptions --


class SubscriptionNotFoundError(YubalError):
    """Raised when a subscription is not found."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "subscription_not_found"

    def __init__(self, subscription_id: UUID) -> None:
        self.subscription_id = subscription_id
        super().__init__(f"Subscription {subscription_id} not found")


class SubscriptionConflictError(YubalError):
    """Raised when a subscription operation conflicts with existing state."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "subscription_conflict"

    def __init__(self, message: str, subscription_id: UUID | None = None) -> None:
        self.subscription_id = subscription_id
        super().__init__(message)


class MetadataFetchError(YubalError):
    """Raised when metadata fetching fails unexpectedly."""

    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "metadata_fetch_failed"

    def __init__(self, message: str, upstream_error: str | None = None) -> None:
        self.upstream_error = upstream_error
        super().__init__(message)


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
    from yubal import (
        APIError,
        AuthenticationRequiredError,
        PlaylistNotFoundError,
        PlaylistParseError,
        UnsupportedPlaylistError,
    )

    # Map yubal core exceptions to HTTP responses
    _CORE_EXCEPTION_MAP: dict[type[Exception], tuple[int, str]] = {
        PlaylistNotFoundError: (404, "playlist_not_found"),
        AuthenticationRequiredError: (401, "authentication_required"),
        PlaylistParseError: (422, "playlist_parse_error"),
        UnsupportedPlaylistError: (422, "unsupported_playlist"),
        APIError: (502, "api_error"),
    }

    for exc_class, (status_code, error_code) in _CORE_EXCEPTION_MAP.items():

        def _make_handler(sc: int, ec: str) -> Any:
            async def handler(request: Request, exc: Exception) -> JSONResponse:
                return JSONResponse(
                    status_code=sc,
                    content={"error": ec, "message": str(exc)},
                )

            return handler

        app.exception_handler(exc_class)(_make_handler(status_code, error_code))

    @app.exception_handler(YubalError)
    async def yubal_error_handler(request: Request, exc: YubalError) -> JSONResponse:
        """Generic handler for all YubalError subclasses."""
        content: dict[str, str | None] = {
            "error": exc.error_code,
            "message": exc.message,
        }

        # Add context fields if present on the exception
        for field in ("job_id", "subscription_id", "upstream_error"):
            value = getattr(exc, field, None)
            if value is not None:
                content[field] = str(value)

        return JSONResponse(status_code=exc.status_code, content=content)
