"""Entry point for running yubal-api as a module: python -m yubal_api."""

import sys

import uvicorn
from pydantic import ValidationError

from yubal_api.settings import get_settings


def main() -> None:
    """Start the FastAPI server."""
    try:
        settings = get_settings()
    except ValidationError as e:
        print(f"Configuration error: {e.errors()[0]['msg']}", file=sys.stderr)
        sys.exit(1)
    uvicorn.run(
        "yubal_api.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
