"""Version command."""

from importlib.metadata import version

import typer


def version_cmd() -> None:
    """Show the yubal version."""
    typer.echo(f"yubal {version('yubal')}")
