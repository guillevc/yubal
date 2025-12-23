"""Doctor command."""
from pathlib import Path

import typer

from app.cli.utils import (
    DEFAULT_BEETS_CONFIG,
    DEFAULT_LIBRARY_DIR,
    create_tagger,
    echo_error,
    echo_info,
    echo_success,
)


def doctor(
    library_dir: Path = typer.Option(
        DEFAULT_LIBRARY_DIR,
        "--library-dir", "-l",
        help="Library directory for organized music",
    ),
    beets_config: Path = typer.Option(
        DEFAULT_BEETS_CONFIG,
        "--beets-config", "-c",
        help="Path to beets configuration file",
    ),
    rebuild: bool = typer.Option(
        False,
        "--rebuild", "-r",
        help="Rebuild database from existing library files if unhealthy",
    ),
) -> None:
    """
    Check library health and optionally repair.

    Verifies the beets database is in sync with the library folder.
    Use --rebuild to re-register existing albums if the database is missing or corrupt.
    """
    tagger = create_tagger(library_dir, beets_config)

    echo_info("Checking library health...")
    health = tagger.check_library_health()

    echo_info(f"  Library folder: {library_dir}")
    echo_info(f"  Albums in folder: {health.library_album_count}")
    echo_info(f"  Albums in database: {health.database_album_count}")
    echo_info("")

    if health.healthy:
        echo_success(health.message)
        return

    typer.echo(typer.style(f"Issue: {health.message}", fg=typer.colors.YELLOW))

    if not rebuild:
        echo_info("")
        echo_info("Run with --rebuild to repair the database")
        raise typer.Exit(1)

    echo_info("")
    echo_info("Rebuilding database...")
    success, message = tagger.rebuild_database()

    if success:
        echo_success(message)
        echo_info("")
        echo_info("Verifying...")
        new_health = tagger.check_library_health()
        echo_info(f"  Albums in database: {new_health.database_album_count}")
        if new_health.healthy:
            echo_success("Library is now healthy")
        else:
            typer.echo(typer.style(f"Warning: {new_health.message}", fg=typer.colors.YELLOW))
    else:
        echo_error(message)
