"""Main CLI entry point."""

from typing import Annotated

import typer

from yubal.cli.commands import download_cmd, meta_cmd, tags_cmd, version_cmd
from yubal.cli.logging import setup_logging

app = typer.Typer(
    no_args_is_help=True,
    help="Extract and download from YouTube Music albums and playlists.",
    rich_markup_mode="rich",
)


@app.callback()
def main(
    ctx: typer.Context,
    verbose: Annotated[
        bool, typer.Option("-v", "--verbose", help="Enable debug logging.")
    ] = False,
) -> None:
    """Extract and download from YouTube Music albums and playlists."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose=verbose)


# Register commands
app.command(name="meta")(meta_cmd)
app.command(name="download")(download_cmd)
app.command(name="tags")(tags_cmd)
app.command(name="version")(version_cmd)


if __name__ == "__main__":
    app()
