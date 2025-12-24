"""Sync command."""

from pathlib import Path

import typer

from yubal.cli.utils import (
    DEFAULT_BEETS_CONFIG,
    DEFAULT_LIBRARY_DIR,
    echo_error,
    echo_info,
    echo_success,
    validate_beets_config,
)
from yubal.core.progress import ProgressEvent, ProgressStep
from yubal.services.sync import SyncService


def _cli_progress_callback(event: ProgressEvent) -> None:
    """Handle progress events for CLI output."""
    if event.step == ProgressStep.ERROR:
        # Don't call echo_error here as it raises Exit
        typer.echo(f"Error: {event.message}", err=True)
    elif event.step == ProgressStep.COMPLETE:
        if "Cleaning up" in event.message:
            echo_info(event.message)
        else:
            echo_success(event.message)
    elif event.step == ProgressStep.DOWNLOADING:
        if event.progress is not None and event.progress < 100:
            # In-progress download - print on same line
            print(f"\r  {event.message}", end="", flush=True)
        else:
            echo_info(event.message)
    elif event.step == ProgressStep.STARTING:
        echo_info("\n--- Starting ---")
        echo_info(event.message)
    elif event.step == ProgressStep.TAGGING:
        if "[beets]" in event.message:
            echo_info(f"  {event.message}")
        else:
            echo_info(event.message)
    else:
        echo_info(event.message)


def sync(
    url: str = typer.Argument(..., help="YouTube Music album/playlist URL"),
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
    audio_format: str = typer.Option(
        "mp3",
        "--format",
        "-f",
        help="Audio format (mp3, m4a, opus, etc.)",
    ),
) -> None:
    """
    Download and tag an album in one step.

    Combines download + tag commands: downloads from YouTube,
    then imports and organizes using beets.
    """
    validate_beets_config(beets_config)

    service = SyncService(
        library_dir=library_dir,
        beets_config=beets_config,
        audio_format=audio_format,
    )

    result = service.sync_album(url, progress_callback=_cli_progress_callback)

    if not result.success:
        echo_error(result.error or "Sync failed")
