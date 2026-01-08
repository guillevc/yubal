from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class YubalError(Exception):
    """Base exception for Yubal application."""


class JobConflictError(YubalError):
    """Raised when a job operation conflicts with existing state."""

    def __init__(self, message: str, active_job_id: str | None = None):
        self.message = message
        self.active_job_id = active_job_id
        super().__init__(message)


class JobNotFoundError(YubalError):
    """Raised when a job is not found."""

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id} not found")


class DownloadError(YubalError):
    """Raised when a download operation fails."""


class BeetsImportError(YubalError):
    """Raised when a beets import operation fails."""


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI app."""

    @app.exception_handler(JobConflictError)
    async def job_conflict_handler(
        request: Request, exc: JobConflictError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": exc.message,
                "active_job_id": exc.active_job_id,
            },
        )

    @app.exception_handler(JobNotFoundError)
    async def job_not_found_handler(
        request: Request, exc: JobNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Job {exc.job_id} not found"},
        )
