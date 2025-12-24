"""CLI utilities."""

from pathlib import Path

import typer

from yubal.core.config import DEFAULT_BEETS_CONFIG, DEFAULT_LIBRARY_DIR

__all__ = [
    "DEFAULT_BEETS_CONFIG",
    "DEFAULT_LIBRARY_DIR",
    "create_tagger",
    "echo_error",
    "echo_info",
    "echo_success",
    "validate_beets_config",
    "validate_path_exists",
]


def echo_error(message: str) -> None:
    """Print error message and exit."""
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(1)


def echo_success(message: str) -> None:
    """Print success message."""
    typer.echo(f"Success: {message}")


def echo_info(message: str) -> None:
    """Print info message."""
    typer.echo(message)


def validate_path_exists(path: Path, name: str = "Path") -> None:
    """Validate that a path exists, exit with error if not."""
    if not path.exists():
        echo_error(f"{name} does not exist: {path}")


def validate_beets_config(beets_config: Path) -> None:
    """Validate that beets config exists."""
    if not beets_config.exists():
        echo_error(f"Beets config not found: {beets_config}")


def create_tagger(library_dir: Path, beets_config: Path):
    """Create a Tagger instance with standard configuration."""
    from yubal.services.tagger import Tagger

    return Tagger(
        beets_config=beets_config,
        library_dir=library_dir,
        beets_db=beets_config.parent / "beets.db",
    )
