"""Version command."""
import typer


def version() -> None:
    """Show version information."""
    typer.echo("ytadl version 0.1.0")
