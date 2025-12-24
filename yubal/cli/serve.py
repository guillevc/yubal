"""API server command."""

from pathlib import Path

import typer


def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
    data_dir: Path | None = typer.Option(
        None, "--data-dir", "-d", help="Data/library directory"
    ),
    config_dir: Path | None = typer.Option(
        None, "--config-dir", "-c", help="Config directory (beets config)"
    ),
) -> None:
    """Start the API server."""
    import uvicorn

    from yubal.core import config

    # Override config if CLI options provided
    if data_dir:
        config.DATA_DIR = data_dir.resolve()
        config.DEFAULT_LIBRARY_DIR = config.DATA_DIR
    if config_dir:
        config.CONFIG_DIR = config_dir.resolve()
        config.DEFAULT_BEETS_CONFIG = config.CONFIG_DIR / "config.yaml"
        config.DEFAULT_BEETS_DB = config.CONFIG_DIR / "beets.db"

    uvicorn.run("yubal.api.app:app", host=host, port=port, reload=reload)
