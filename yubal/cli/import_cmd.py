"""Import command for importing existing music files."""

from pathlib import Path

import typer

from yubal.cli.utils import (
    DEFAULT_BEETS_CONFIG,
    DEFAULT_LIBRARY_DIR,
    create_tagger,
    echo_error,
    echo_info,
    echo_success,
    validate_beets_config,
    validate_path_exists,
)


def import_music(
    source: Path = typer.Argument(
        ...,
        help="Path to music files or folder to import",
    ),
    library_dir: Path = typer.Option(
        DEFAULT_LIBRARY_DIR,
        "--library-dir",
        "-l",
        help="Library directory for organized music",
    ),
    beets_config: Path = typer.Option(
        DEFAULT_BEETS_CONFIG,
        "--beets-config",
        "-c",
        help="Path to beets configuration file",
    ),
    copy: bool = typer.Option(
        False,
        "--copy",
        help="Copy files instead of moving (keep originals)",
    ),
    noautotag: bool = typer.Option(
        False,
        "--noautotag",
        "-A",
        help="Skip auto-tagging, trust existing file metadata",
    ),
) -> None:
    """
    Import existing music files into the library.

    Imports files from SOURCE, organizes them according to your beets
    configuration (paths template), and registers them in the database.

    By default, files are moved into the library. Use --copy to keep originals.
    Use --noautotag to skip auto-tagging and trust existing file metadata.

    Examples:
        yubal import ~/Downloads/music
        yubal import ~/old-library --copy
        yubal import ~/Music --noautotag
    """
    validate_path_exists(source, "Source path")
    validate_beets_config(beets_config)

    tagger = create_tagger(library_dir, beets_config)

    echo_info(f"Importing from: {source}")
    echo_info(f"Library: {library_dir}")
    echo_info(f"Mode: {'copy' if copy else 'move'}")
    if noautotag:
        echo_info("Auto-tag: disabled (using existing file metadata)")
    echo_info("")

    success, message, imported_count = tagger.import_files(
        source, copy=copy, noautotag=noautotag
    )

    if success:
        echo_success(message)
        if imported_count > 0:
            echo_info("")
            echo_info("Run 'yubal doctor' to verify library health")
    else:
        echo_error(message)
