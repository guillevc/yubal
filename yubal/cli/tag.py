"""Tag command."""

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


def tag(
    input_dir: Path = typer.Argument(
        ..., help="Directory containing downloaded audio files"
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
        "-C",
        help="Copy to library instead of moving (original files unchanged)",
    ),
) -> None:
    """
    Tag and organize downloaded music using beets.

    Imports audio files, fetches metadata from Spotify/MusicBrainz,
    and organizes into the library structure.
    """
    validate_path_exists(input_dir, "Input directory")
    validate_beets_config(beets_config)

    echo_info(f"Source: {input_dir}")
    echo_info(f"Library: {library_dir}")
    if copy:
        echo_info("Mode: copy (original files will be preserved)")

    tagger = create_tagger(library_dir, beets_config)

    result = tagger.tag_album(input_dir, copy=copy)

    if not result.success:
        echo_error(result.error or "Tagging failed")

    echo_info(f"Tagged {result.track_count} tracks")
    if result.dest_dir:
        if copy:
            echo_success(f"Copied and tagged to: {result.dest_dir}")
        else:
            echo_success(f"Moved and tagged to: {result.dest_dir}")
    else:
        echo_success("Tagging complete")
