"""Nuke command."""

import shutil
from pathlib import Path

import typer

from yubal.cli.utils import (
    DEFAULT_BEETS_CONFIG,
    DEFAULT_LIBRARY_DIR,
    echo_info,
    echo_success,
)


def nuke(
    library_dir: Path = typer.Option(
        DEFAULT_LIBRARY_DIR,
        "--library-dir",
        "-l",
        help="Library directory to remove",
    ),
    beets_config: Path = typer.Option(
        DEFAULT_BEETS_CONFIG,
        "--beets-config",
        "-c",
        help="Path to beets configuration file (used to find db/logs)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Remove all data: library, database, logs, and state files.

    This is destructive and cannot be undone. Use --force to skip confirmation.
    """
    config_dir = beets_config.parent

    targets = [
        ("Library", library_dir),
        ("Database", config_dir / "beets.db"),
        ("Import log", config_dir / "beets_import.log"),
        ("State", config_dir / "state.pickle"),
    ]

    existing = [(name, path) for name, path in targets if path.exists()]

    if not existing:
        echo_info("Nothing to remove - already clean")
        return

    echo_info("Will remove:")
    for name, path in existing:
        if path.is_dir():
            item_count = sum(1 for _ in path.rglob("*") if _.is_file())
            echo_info(f"  - {name}: {path} ({item_count} files)")
        else:
            echo_info(f"  - {name}: {path}")

    if not force:
        echo_info("")
        confirm = typer.confirm("This cannot be undone. Continue?", default=False)
        if not confirm:
            echo_info("Aborted")
            raise typer.Exit(0)

    for name, path in existing:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        echo_info(f"  Removed {name}")

    echo_success("All data removed")
