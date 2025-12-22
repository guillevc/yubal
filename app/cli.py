"""YTAD - YouTube Album Downloader CLI."""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import typer
import typer.main

from app.services.downloader import Downloader
from app.services.tagger import Tagger

def help_all_callback(ctx: typer.Context, value: bool) -> None:
    """Print help for all commands."""
    if not value:
        return

    click = typer.main.click

    # Get all commands from the Click group
    click_app = ctx.command
    for name in sorted(click_app.commands.keys()):
        cmd = click_app.commands[name]
        # Create a context for the subcommand (without validating args)
        with click.Context(cmd, info_name=f"ytad {name}") as cmd_ctx:
            typer.echo(cmd.get_help(cmd_ctx))
    raise typer.Exit()

app = typer.Typer(
    name="ytad",
    help="YouTube Album Downloader - Download and organize music from YouTube",
    no_args_is_help=True,
)

@app.callback()
def main_callback(
    ctx: typer.Context,
    help_all: bool = typer.Option(
        False,
        "--help-all",
        callback=help_all_callback,
        is_eager=True,
        help="Show help for all commands",
    ),
) -> None:
    """YouTube Album Downloader - Download and organize music from YouTube."""
    pass

# Default paths
DEFAULT_BEETS_CONFIG = Path(__file__).parent.parent / "config" / "beets_config.yaml"
DEFAULT_LIBRARY_DIR = Path(__file__).parent.parent / "data"

def echo_error(message: str) -> None:
    """Print error message and exit."""
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(1)


def echo_success(message: str) -> None:
    """Print success message."""
    typer.echo(f"Success: {message}")


def echo_info(message: str) -> None:
    """Print info message."""
    typer.echo(message)

@app.command()
def download(
    url: str = typer.Argument(..., help="YouTube Music album/playlist URL"),
    output_dir: Path = typer.Option(
        ...,
        "--output-dir", "-o",
        help="Directory to save downloaded files",
    ),
    audio_format: str = typer.Option(
        "mp3",
        "--format", "-f",
        help="Audio format (mp3, m4a, opus, etc.)",
    ),
) -> None:
    """
    Download an album/playlist from YouTube Music.

    Downloads all tracks, embeds metadata, and saves to the specified directory.
    """
    echo_info(f"Downloading from: {url}")
    echo_info(f"Output directory: {output_dir}")

    downloader = Downloader(audio_format=audio_format)

    result = downloader.download_album(url, output_dir)

    if not result.success:
        echo_error(result.error or "Download failed")

    echo_info(f"Downloaded {len(result.downloaded_files)} tracks:")
    for f in sorted(result.downloaded_files):
        echo_info(f"  - {f.name}")

    if result.album_info:
        echo_success(
            f"Album: {result.album_info.title} by {result.album_info.artist} "
            f"({result.album_info.track_count} tracks)"
        )

@app.command()
def tag(
    input_dir: Path = typer.Argument(..., help="Directory containing downloaded audio files"),
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
    copy: bool = typer.Option(
        False,
        "--copy", "-C",
        help="Copy to library instead of moving (original files unchanged)",
    ),
) -> None:
    """
    Tag and organize downloaded music using beets.

    Imports audio files, fetches metadata from Spotify/MusicBrainz,
    and organizes into the library structure.
    """
    if not input_dir.exists():
        echo_error(f"Input directory does not exist: {input_dir}")

    if not beets_config.exists():
        echo_error(f"Beets config not found: {beets_config}")

    echo_info(f"Source: {input_dir}")
    echo_info(f"Library: {library_dir}")
    if copy:
        echo_info("Mode: copy (original files will be preserved)")

    tagger = Tagger(
        beets_config=beets_config,
        library_dir=library_dir,
        beets_db=beets_config.parent / "beets.db",
    )

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

@app.command()
def sync(
    url: str = typer.Argument(..., help="YouTube Music album/playlist URL"),
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
    audio_format: str = typer.Option(
        "mp3",
        "--format", "-f",
        help="Audio format (mp3, m4a, opus, etc.)",
    ),
) -> None:
    """
    Download and tag an album in one step.

    Combines download + tag commands: downloads from YouTube,
    then imports and organizes using beets.
    """
    if not beets_config.exists():
        echo_error(f"Beets config not found: {beets_config}")

    # Create temp directory for download
    temp_dir = Path(tempfile.mkdtemp(prefix="ytad_"))
    echo_info(f"Temp directory: {temp_dir}")

    try:
        # Step 1: Download
        echo_info(f"\n--- Step 1: Download ---")
        echo_info(f"URL: {url}")

        downloader = Downloader(audio_format=audio_format)
        download_result = downloader.download_album(url, temp_dir)

        if not download_result.success:
            echo_error(download_result.error or "Download failed")

        echo_info(f"Downloaded {len(download_result.downloaded_files)} tracks")
        if download_result.album_info:
            echo_info(
                f"Album: {download_result.album_info.title} "
                f"by {download_result.album_info.artist}"
            )

        # Step 2: Tag
        echo_info(f"\n--- Step 2: Tag ---")

        tagger = Tagger(
            beets_config=beets_config,
            library_dir=library_dir,
            beets_db=beets_config.parent / "beets.db",
        )

        tag_result = tagger.tag_album(temp_dir)

        if not tag_result.success:
            echo_error(tag_result.error or "Tagging failed")

        echo_info(f"Tagged {tag_result.track_count} tracks")

        # Success
        echo_info(f"\n--- Complete ---")
        if tag_result.dest_dir:
            echo_success(f"Album saved to: {tag_result.dest_dir}")
        else:
            echo_success("Sync complete")

    finally:
        # Cleanup temp directory
        if temp_dir.exists():
            echo_info(f"Cleaning up temp directory...")
            shutil.rmtree(temp_dir, ignore_errors=True)


def get_audio_tags(file_path: Path) -> dict[str, str]:
    """Extract metadata tags from an audio file using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(file_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return data.get("format", {}).get("tags", {})


def truncate_value(value: str, max_length: int = 45) -> str:
    """Truncate a string and add ellipsis if too long."""
    value = str(value).replace("\n", " ").strip()
    if len(value) > max_length:
        return value[: max_length - 3] + "..."
    return value


def print_metadata_table(tags: dict[str, str]) -> None:
    """Print metadata tags in a formatted table."""
    priority_tags = ["title", "artist", "album", "album_artist", "track", "date", "genre"]
    skip_tags = {"encoder"}

    # Build rows: priority tags first, then remaining sorted
    rows: list[tuple[str, str]] = []
    for key in priority_tags:
        if key in tags:
            rows.append((key, truncate_value(tags[key])))

    for key in sorted(tags.keys()):
        if key not in priority_tags and key not in skip_tags:
            rows.append((key, truncate_value(tags[key])))

    # Calculate column widths
    tag_width = max((len(r[0]) for r in rows), default=3)
    val_width = max((len(r[1]) for r in rows), default=5)

    # ANSI escape codes add extra characters, so we need padding offsets
    bold_offset = 8
    color_offset = 9

    # Print table
    echo_info("")
    header_tag = typer.style("Tag", bold=True)
    header_val = typer.style("Value", bold=True)
    typer.echo(f"| {header_tag:<{tag_width + bold_offset}} | {header_val:<{val_width + bold_offset}} |")
    echo_info(f"|{'-' * (tag_width + 2)}|{'-' * (val_width + 2)}|")

    for key, value in rows:
        styled_key = typer.style(key, fg=typer.colors.CYAN)
        typer.echo(f"| {styled_key:<{tag_width + color_offset}} | {value:<{val_width}} |")


@app.command()
def info(
    file_path: Path = typer.Argument(..., help="Audio file to inspect"),
) -> None:
    """
    Display metadata tags of an audio file.

    Shows embedded ID3/Vorbis tags in a table format.
    """
    if not file_path.exists():
        echo_error(f"File not found: {file_path}")

    try:
        tags = get_audio_tags(file_path)
        if not tags:
            echo_info("No metadata tags found.")
            return
        print_metadata_table(tags)
    except subprocess.CalledProcessError:
        echo_error("ffprobe failed. Is ffmpeg installed?")
    except json.JSONDecodeError:
        echo_error("Failed to parse ffprobe output")


@app.command()
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
    tagger = Tagger(
        beets_config=beets_config,
        library_dir=library_dir,
        beets_db=beets_config.parent / "beets.db",
    )

    echo_info("Checking library health...")
    health = tagger.check_library_health()

    # Display status
    echo_info(f"  Library folder: {library_dir}")
    echo_info(f"  Albums in folder: {health.library_album_count}")
    echo_info(f"  Albums in database: {health.database_album_count}")
    echo_info("")

    if health.healthy:
        echo_success(health.message)
        return

    # Unhealthy state
    typer.echo(typer.style(f"Issue: {health.message}", fg=typer.colors.YELLOW))

    if not rebuild:
        echo_info("")
        echo_info("Run with --rebuild to repair the database")
        raise typer.Exit(1)

    # Rebuild requested
    echo_info("")
    echo_info("Rebuilding database...")
    success, message = tagger.rebuild_database()

    if success:
        echo_success(message)
        # Verify after rebuild
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


@app.command()
def nuke(
    library_dir: Path = typer.Option(
        DEFAULT_LIBRARY_DIR,
        "--library-dir", "-l",
        help="Library directory to remove",
    ),
    beets_config: Path = typer.Option(
        DEFAULT_BEETS_CONFIG,
        "--beets-config", "-c",
        help="Path to beets configuration file (used to find db/logs)",
    ),
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Skip confirmation prompt",
    ),
) -> None:
    """
    Remove all data: library, database, logs, and state files.

    This is destructive and cannot be undone. Use --force to skip confirmation.
    """
    config_dir = beets_config.parent

    # Files to remove
    targets = [
        ("Library", library_dir),
        ("Database", config_dir / "beets.db"),
        ("Import log", config_dir / "beets_import.log"),
        ("State", config_dir / "state.pickle"),
    ]

    # Check what exists
    existing = [(name, path) for name, path in targets if path.exists()]

    if not existing:
        echo_info("Nothing to remove - already clean")
        return

    # Show what will be removed
    echo_info("Will remove:")
    for name, path in existing:
        if path.is_dir():
            # Count items in directory
            item_count = sum(1 for _ in path.rglob("*") if _.is_file())
            echo_info(f"  - {name}: {path} ({item_count} files)")
        else:
            echo_info(f"  - {name}: {path}")

    # Confirm
    if not force:
        echo_info("")
        confirm = typer.confirm("This cannot be undone. Continue?", default=False)
        if not confirm:
            echo_info("Aborted")
            raise typer.Exit(0)

    # Remove
    for name, path in existing:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        echo_info(f"  Removed {name}")

    echo_success("All data removed")


@app.command()
def version() -> None:
    """Show version information."""
    typer.echo("ytad version 0.1.0")


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
