"""Entry point for running yubal as a module: python -m yubal."""

import uvicorn


def main() -> None:
    """Start the FastAPI server."""
    uvicorn.run(
        "yubal.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
