"""FastAPI application module."""

from yubal.api.app import app

__all__ = ["app"]


def run() -> None:
    """Run the API server."""
    import uvicorn

    uvicorn.run(
        "app.api.app:app",
        host="0.0.0.0",  # noqa: S104 - intentional for server accessibility
        port=8000,
        reload=True,
    )
