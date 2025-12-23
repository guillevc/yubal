"""YTADL CLI - command registration and entry point."""
from app.cli.app import app
from app.cli.doctor import doctor
from app.cli.download import download
from app.cli.info import info
from app.cli.nuke import nuke
from app.cli.sync import sync
from app.cli.tag import tag
from app.cli.version import version

# Explicit command registration
app.command()(doctor)
app.command()(download)
app.command()(info)
app.command()(nuke)
app.command()(sync)
app.command()(tag)
app.command()(version)


def main() -> None:
    """Entry point for the CLI."""
    app()
