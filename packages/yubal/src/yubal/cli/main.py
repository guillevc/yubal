"""Main CLI entry point."""

import click

from yubal.cli.commands import register_commands
from yubal.cli.logging import setup_logging


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Extract and download from YouTube Music albums and playlists."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose=verbose)


# Register all commands with the main group
register_commands(main)


if __name__ == "__main__":
    main()
