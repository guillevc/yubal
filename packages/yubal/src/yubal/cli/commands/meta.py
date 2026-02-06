"""Meta command for extracting YouTube Music metadata."""

import json
import logging
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress

from yubal.cli.formatting import (
    PROGRESS_COLUMNS,
    print_tracks,
    print_unavailable_tracks,
)
from yubal.cli.logging import setup_logging
from yubal.cli.state import ExtractionState
from yubal.client import YTMusicClient
from yubal.exceptions import YTMetaError
from yubal.models.enums import SkipReason
from yubal.services import MetadataExtractorService
from yubal.utils.url import is_single_track_url

logger = logging.getLogger("yubal")


def print_no_tracks_message(console: Console, state: ExtractionState) -> None:
    """Print appropriate message when no tracks were extracted."""
    if SkipReason.NO_ALBUM_MATCH in state.skipped_by_reason:
        console.print(
            "[yellow]Track skipped: Could not find matching album info "
            "(search results didn't match track title/artist)[/yellow]"
        )
    elif SkipReason.UNSUPPORTED_VIDEO_TYPE in state.skipped_by_reason:
        console.print(
            "[yellow]Track skipped: Unsupported video type "
            "(only ATV and OMV are supported)[/yellow]"
        )
    else:
        console.print(
            "[yellow]No tracks found (may be unsupported video type)[/yellow]"
        )
    if state.unavailable_tracks:
        print_unavailable_tracks(console, state.unavailable_tracks)


def meta_cmd(
    ctx: typer.Context,
    url: Annotated[str, typer.Argument(metavar="URL")],
    as_json: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
    cookies: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            file_okay=True,
            dir_okay=False,
            help="Path to cookies.txt for YouTube Music authentication.",
        ),
    ] = None,
) -> None:
    """Extract structured metadata from a YouTube Music URL.

    URL can be either a single track URL or a playlist/album URL.
    The content type is automatically detected.

    Examples:

        yubal meta "https://music.youtube.com/watch?v=VIDEO_ID"

        yubal meta "https://music.youtube.com/playlist?list=OLAK5uy_xxx"

        yubal meta "https://music.youtube.com/playlist?list=PLxxx"
    """
    console = Console()
    verbose = ctx.obj.get("verbose", False)

    # Reconfigure logging to use this console so logs appear above progress bar
    setup_logging(verbose=verbose, console=console)

    try:
        client = YTMusicClient(cookies_path=cookies)
        service = MetadataExtractorService(client)
        state = ExtractionState()

        # Inform user about single track detection (early feedback)
        if is_single_track_url(url):
            console.print("[cyan]Detected single track[/cyan]")

        # Unified extraction API handles all URL types
        with Progress(*PROGRESS_COLUMNS, console=console) as progress:
            task = progress.add_task("Extracting metadata", total=None)

            for extract_progress in service.extract(url):
                progress.update(
                    task,
                    completed=extract_progress.current,
                    total=extract_progress.total - extract_progress.skipped,
                )
                state.update_from_progress(extract_progress)

        if not state.tracks:
            print_no_tracks_message(console, state)
            return

        if as_json:
            data = [t.model_dump() for t in state.tracks]
            json.dump(data, sys.stdout, indent=2, ensure_ascii=False, default=str)
        else:
            print_tracks(
                console,
                state.tracks,
                skipped=state.skipped,
                unavailable=state.unavailable,
                kind=state.playlist_kind,
                title=state.playlist_title,
                unavailable_tracks=state.unavailable_tracks,
            )

    except YTMetaError as e:
        logger.error(str(e))
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1) from e
