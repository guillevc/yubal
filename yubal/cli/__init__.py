"""YTADL CLI - command registration and entry point."""

from yubal.cli.app import app
from yubal.cli.doctor import doctor
from yubal.cli.download import download
from yubal.cli.import_cmd import import_music
from yubal.cli.info import info
from yubal.cli.nuke import nuke
from yubal.cli.serve import serve
from yubal.cli.sync import sync
from yubal.cli.tag import tag
from yubal.cli.version import version

# Explicit command registration
app.command()(doctor)
app.command()(download)
app.command(name="import")(import_music)
app.command()(info)
app.command()(nuke)
app.command()(serve)
app.command()(sync)
app.command()(tag)
app.command()(version)


def main() -> None:
    """Entry point for the CLI."""
    app()
