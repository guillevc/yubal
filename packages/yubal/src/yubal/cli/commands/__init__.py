"""CLI commands package."""

import click

from yubal.cli.commands.download import download_cmd
from yubal.cli.commands.meta import meta_cmd
from yubal.cli.commands.tags import tags_cmd


def register_commands(group: click.Group) -> None:
    """Register all CLI commands with the main group."""
    group.add_command(meta_cmd)
    group.add_command(download_cmd)
    group.add_command(tags_cmd)
