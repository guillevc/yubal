#!/usr/bin/env python3
"""Command-line interface for ytmeta.

This CLI is primarily for debugging and development.
For production use, import ytmeta as a library.
"""

import json
import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from ytmeta.client import YTMusicClient
from ytmeta.config import DownloadConfig
from ytmeta.exceptions import YTMetaError
from ytmeta.models.domain import TrackMetadata
from ytmeta.services import (
    DownloadResult,
    DownloadService,
    DownloadStatus,
    MetadataExtractorService,
)

logger = logging.getLogger("ytmeta")


def setup_logging() -> None:
    """Configure logging with Rich handler."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def print_table(tracks: list[TrackMetadata]) -> None:
    """Print tracks as a Rich table.

    Args:
        tracks: List of track metadata to display.
    """
    console = Console()
    table = Table(show_header=True, header_style="bold")

    table.add_column("OMV ID")
    table.add_column("ATV ID")
    table.add_column("Title")
    table.add_column("Artist")
    table.add_column("Album")
    table.add_column("Year")
    table.add_column("#", justify="right")
    table.add_column("Type")

    for t in tracks:
        table.add_row(
            t.omv_video_id,
            t.atv_video_id or "",
            t.title,
            t.artist,
            t.album,
            t.year or "",
            str(t.tracknumber) if t.tracknumber else "",
            t.video_type,
        )

    console.print(table)
    console.print(f"\nExtracted {len(tracks)} track(s)")


@click.group()
def main() -> None:
    """Extract metadata from YouTube Music playlists."""
    setup_logging()


@main.command(name="meta")
@click.argument("url", metavar="PLAYLIST_URL")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
def meta_cmd(url: str, as_json: bool) -> None:
    """Extract structured metadata from a playlist.

    PLAYLIST_URL should be a full YouTube Music playlist URL like:
    https://music.youtube.com/playlist?list=PLxxxxxxxx
    """
    try:
        client = YTMusicClient()
        service = MetadataExtractorService(client)
        tracks = service.extract(url)

        if as_json:
            data = [t.model_dump() for t in tracks]
            json.dump(data, sys.stdout, indent=2, ensure_ascii=False, default=str)
        else:
            print_table(tracks)

    except YTMetaError as e:
        logger.error(str(e))
        raise click.ClickException(str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error")
        raise click.ClickException(f"Unexpected error: {e}") from e


@main.command(name="download")
@click.argument("url", metavar="PLAYLIST_URL")
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path),
    default=Path.cwd(),
    help="Output directory for downloaded files (default: current directory).",
)
@click.option(
    "--codec",
    type=click.Choice(["opus", "mp3", "m4a"]),
    default="opus",
    help="Audio codec (default: opus).",
)
def download_cmd(
    url: str,
    output: Path,
    codec: str,
) -> None:
    """Download tracks from a YouTube Music playlist.

    PLAYLIST_URL should be a full YouTube Music playlist URL like:
    https://music.youtube.com/playlist?list=PLxxxxxxxx

    Downloads each track using yt-dlp, preferring the ATV (Audio Track Video)
    version for better audio quality, falling back to OMV (Official Music Video)
    if ATV is unavailable. Existing files are automatically skipped.

    Examples:

        ytmeta download "https://music.youtube.com/playlist?list=PLxxx"

        ytmeta download "https://music.youtube.com/playlist?list=PLxxx" -o ~/Music
    """
    console = Console()

    try:
        # Step 1: Extract metadata
        console.print("[bold]Extracting playlist metadata...[/bold]")

        client = YTMusicClient()
        extractor = MetadataExtractorService(client)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Extracting metadata", total=None)

            def on_extract_progress(current: int, total: int) -> None:
                progress.update(task, completed=current, total=total)

            tracks = extractor.extract(url, on_progress=on_extract_progress)

        console.print(f"[green]Found {len(tracks)} tracks[/green]\n")

        # Show track summary
        table = Table(show_header=True, header_style="bold")
        table.add_column("#", justify="right", width=4)
        table.add_column("Artist")
        table.add_column("Title")
        table.add_column("Source", width=6)

        for i, track in enumerate(tracks, 1):
            source = "ATV" if track.atv_video_id else "OMV"
            table.add_row(str(i), track.artist, track.title, source)

        console.print(table)
        console.print()

        # Step 2: Download tracks
        console.print(f"[bold]Downloading to {output}...[/bold]\n")

        from ytmeta.config import AudioCodec

        config = DownloadConfig(
            base_path=output,
            codec=AudioCodec(codec),
            quiet=True,  # We handle our own progress display
        )
        downloader = DownloadService(config)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            overall_task = progress.add_task("Downloading", total=len(tracks))

            def on_progress(current: int, total: int, result: DownloadResult) -> None:
                status_icon = {
                    DownloadStatus.SUCCESS: "[green]OK[/green]",
                    DownloadStatus.SKIPPED: "[yellow]SKIP[/yellow]",
                    DownloadStatus.FAILED: "[red]FAIL[/red]",
                }
                progress.update(overall_task, completed=current)
                console.print(
                    f"  [{current}/{total}] {result.track.artist} - "
                    f"{result.track.title}: {status_icon[result.status]}"
                )

            results = downloader.download_tracks(tracks, on_progress=on_progress)

        # Step 3: Show results summary
        console.print()
        successful = [r for r in results if r.status == DownloadStatus.SUCCESS]
        skipped = [r for r in results if r.status == DownloadStatus.SKIPPED]
        failed = [r for r in results if r.status == DownloadStatus.FAILED]

        console.print(
            f"[green]Downloaded: {len(successful)}[/green] | "
            f"[yellow]Skipped: {len(skipped)}[/yellow] | "
            f"[red]Failed: {len(failed)}[/red]"
        )

        if failed:
            console.print("\n[red]Failed downloads:[/red]")
            for result in failed:
                console.print(
                    f"  [red]- {result.track.artist} - {result.track.title}: "
                    f"{result.error}[/red]"
                )

    except YTMetaError as e:
        logger.error(str(e))
        raise click.ClickException(str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error")
        raise click.ClickException(f"Unexpected error: {e}") from e


if __name__ == "__main__":
    main()
