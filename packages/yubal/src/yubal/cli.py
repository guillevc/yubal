#!/usr/bin/env python3
"""Command-line interface for yubal.

This CLI is primarily for debugging and development.
For production use, import yubal as a library.
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

from yubal.client import YTMusicClient
from yubal.config import AudioCodec, DownloadConfig, PlaylistDownloadConfig
from yubal.exceptions import YTMetaError
from yubal.models.domain import DownloadStatus, TrackMetadata
from yubal.services import MetadataExtractorService, PlaylistDownloadService

logger = logging.getLogger("yubal")


def setup_logging() -> None:
    """Configure logging with Rich handler."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def print_table(
    tracks: list[TrackMetadata],
    skipped: int = 0,
    unavailable: int = 0,
    playlist_total: int = 0,
    kind: str | None = None,
    title: str | None = None,
) -> None:
    """Print tracks as a Rich table.

    Args:
        tracks: List of track metadata to display.
        skipped: Number of tracks skipped (unsupported video type).
        unavailable: Number of tracks unavailable (no videoId).
        playlist_total: Total tracks in playlist (0 means no limit applied).
        kind: Content kind ("album" or "playlist").
        title: Title of the album/playlist.
    """
    console = Console()
    table = Table(show_header=True, header_style="bold", show_lines=True)

    table.add_column("OMV ID")
    table.add_column("ATV ID")
    table.add_column("Title")
    table.add_column("Artist")
    table.add_column("Album")
    table.add_column("Album Artist")
    table.add_column("Track", justify="right")
    table.add_column("Year")
    table.add_column("Cover URL")
    table.add_column("Type")

    for t in tracks:
        # Format track number as "N/Total" or just "N" or empty
        if t.track_number and t.total_tracks:
            track_str = f"{t.track_number}/{t.total_tracks}"
        elif t.track_number:
            track_str = str(t.track_number)
        else:
            track_str = ""

        table.add_row(
            t.omv_video_id or "",
            t.atv_video_id or "",
            t.title,
            t.artist,
            t.album,
            t.album_artist,
            track_str,
            t.year or "",
            t.cover_url or "",
            t.video_type,
        )

    # Print header with kind and title
    if kind and title:
        kind_label = kind.capitalize()
        console.print(f"\n[bold cyan]{kind_label}:[/bold cyan] {title}")

    console.print(table)

    # Build summary message
    track_count = len(tracks)
    is_limited = playlist_total > 0 and track_count < playlist_total
    kind_suffix = f" from {kind}" if kind else ""

    if is_limited:
        # Show "X of Y tracks" when limit is applied
        msg = (
            f"\nDownloading [cyan]{track_count}[/cyan] "
            f"of [cyan]{playlist_total}[/cyan] tracks{kind_suffix}"
        )
    else:
        msg = f"\nExtracted {track_count} track(s){kind_suffix}"

    # Add skipped/unavailable info
    summary_parts = []
    if skipped > 0:
        summary_parts.append(f"[yellow]{skipped} skipped[/yellow] (unsupported type)")
    if unavailable > 0:
        summary_parts.append(
            f"[yellow]{unavailable} unavailable[/yellow] (no video/not music)"
        )

    if summary_parts:
        msg += f" ({', '.join(summary_parts)})"

    console.print(msg)


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
    console = Console()

    try:
        client = YTMusicClient()
        service = MetadataExtractorService(client)

        tracks: list[TrackMetadata] = []
        skipped = 0
        unavailable = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Extracting metadata", total=None)

            for extract_progress in service.extract(url):
                progress.update(
                    task,
                    completed=extract_progress.current,
                    total=extract_progress.total - extract_progress.skipped,
                )
                tracks.append(extract_progress.track)
                skipped = extract_progress.skipped
                unavailable = extract_progress.unavailable

        if as_json:
            data = [t.model_dump() for t in tracks]
            json.dump(data, sys.stdout, indent=2, ensure_ascii=False, default=str)
        else:
            print_table(tracks, skipped=skipped, unavailable=unavailable)

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
@click.option(
    "--max-items",
    type=int,
    default=None,
    help="Maximum number of tracks to download (playlists only, not albums).",
)
def download_cmd(
    url: str,
    output: Path,
    codec: str,
    max_items: int | None,
) -> None:
    """Download tracks from a YouTube Music playlist.

    PLAYLIST_URL should be a full YouTube Music playlist URL like:
    https://music.youtube.com/playlist?list=PLxxxxxxxx

    Downloads each track using yt-dlp, preferring the ATV (Audio Track Video)
    version for better audio quality, falling back to OMV (Official Music Video)
    if ATV is unavailable. Existing files are automatically skipped.

    Examples:

        yubal download "https://music.youtube.com/playlist?list=PLxxx"

        yubal download "https://music.youtube.com/playlist?list=PLxxx" -o ~/Music
    """
    console = Console()

    try:
        # Configure the playlist download service
        config = PlaylistDownloadConfig(
            download=DownloadConfig(
                base_path=output,
                codec=AudioCodec(codec),
                quiet=True,
            ),
            max_items=max_items,
        )
        service = PlaylistDownloadService(config)

        # Status icons for display
        status_icon = {
            DownloadStatus.SUCCESS: "[green]OK[/green]",
            DownloadStatus.SKIPPED: "[yellow]SKIP[/yellow]",
            DownloadStatus.FAILED: "[red]FAIL[/red]",
        }

        # Track extraction info for table display
        tracks: list[TrackMetadata] = []
        skipped = 0
        unavailable = 0
        playlist_total = 0
        playlist_kind: str | None = None
        playlist_title: str | None = None

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            extract_task = progress.add_task("Extracting metadata", total=None)
            download_task = progress.add_task("Downloading", total=None, visible=False)

            for p in service.download_playlist(url):
                if p.phase == "extracting" and p.extract_progress:
                    ep = p.extract_progress
                    progress.update(
                        extract_task,
                        completed=ep.current,
                        total=ep.total - ep.skipped,
                    )
                    tracks.append(ep.track)
                    skipped = ep.skipped
                    unavailable = ep.unavailable
                    playlist_total = ep.playlist_total
                    playlist_kind = ep.playlist_info.kind.value
                    playlist_title = ep.playlist_info.title

                elif p.phase == "downloading" and p.download_progress:
                    # Hide extract task, show download task on first download
                    if not progress.tasks[download_task].visible:
                        progress.update(extract_task, visible=False)
                        progress.update(download_task, visible=True)
                        # Show track table before downloads
                        console.print()
                        print_table(
                            tracks,
                            skipped=skipped,
                            unavailable=unavailable,
                            playlist_total=playlist_total,
                            kind=playlist_kind,
                            title=playlist_title,
                        )
                        console.print()
                        console.print(f"[bold]Downloading to {output}...[/bold]\n")

                    dp = p.download_progress
                    progress.update(download_task, completed=dp.current, total=dp.total)
                    result = dp.result
                    console.print(
                        f"  [{dp.current}/{dp.total}] "
                        f"{result.track.artist} - {result.track.title}: "
                        f"{status_icon[result.status]}"
                    )

        # Get final result
        result = service.get_result()
        if not result:
            console.print("[yellow]No tracks found in playlist[/yellow]")
            return

        # Show summary
        console.print()
        console.print(
            f"[green]Downloaded: {result.success_count}[/green] | "
            f"[yellow]Skipped: {result.skipped_count}[/yellow] | "
            f"[red]Failed: {result.failed_count}[/red]"
        )

        # Show failed downloads
        failed = [
            r for r in result.download_results if r.status == DownloadStatus.FAILED
        ]
        if failed:
            console.print("\n[red]Failed downloads:[/red]")
            for r in failed:
                console.print(
                    f"  [red]- {r.track.artist} - {r.track.title}: {r.error}[/red]"
                )

        # Show generated files
        if result.m3u_path:
            console.print(f"\n[cyan]M3U playlist saved:[/cyan] {result.m3u_path}")
        if result.cover_path:
            console.print(f"[cyan]Playlist cover saved:[/cyan] {result.cover_path}")

    except YTMetaError as e:
        logger.error(str(e))
        raise click.ClickException(str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error")
        raise click.ClickException(f"Unexpected error: {e}") from e


if __name__ == "__main__":
    main()
