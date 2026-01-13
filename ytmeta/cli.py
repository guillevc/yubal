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
    DownloadService,
    DownloadStatus,
    MetadataExtractorService,
    PlaylistInfo,
)
from ytmeta.utils import is_album_playlist, write_m3u

logger = logging.getLogger("ytmeta")


def setup_logging() -> None:
    """Configure logging with Rich handler."""
    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def print_table(
    tracks: list[TrackMetadata], skipped: int = 0, unavailable: int = 0
) -> None:
    """Print tracks as a Rich table.

    Args:
        tracks: List of track metadata to display.
        skipped: Number of tracks skipped (unsupported video type).
        unavailable: Number of tracks unavailable (no videoId).
    """
    console = Console()
    table = Table(show_header=True, header_style="bold")

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

    console.print(table)

    # Build summary message with optional skipped/unavailable info
    summary_parts = []
    if skipped > 0:
        summary_parts.append(f"[yellow]{skipped} skipped[/yellow] (unsupported type)")
    if unavailable > 0:
        summary_parts.append(
            f"[yellow]{unavailable} unavailable[/yellow] (no video/not music)"
        )

    if summary_parts:
        console.print(f"\nExtracted {len(tracks)} track(s) ({', '.join(summary_parts)})")
    else:
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

        tracks: list[TrackMetadata] = []
        playlist_info: PlaylistInfo | None = None
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

            for extract_progress in extractor.extract(url):
                progress.update(
                    task,
                    completed=extract_progress.current,
                    total=extract_progress.total - extract_progress.skipped,
                )
                if extract_progress.track:
                    tracks.append(extract_progress.track)
                skipped = extract_progress.skipped
                unavailable = extract_progress.unavailable
                # Capture playlist info from the first progress event
                if playlist_info is None:
                    playlist_info = extract_progress.playlist_info

        console.print()
        print_table(tracks, skipped=skipped, unavailable=unavailable)
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

        results = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            overall_task = progress.add_task("Downloading", total=len(tracks))

            status_icon = {
                DownloadStatus.SUCCESS: "[green]OK[/green]",
                DownloadStatus.SKIPPED: "[yellow]SKIP[/yellow]",
                DownloadStatus.FAILED: "[red]FAIL[/red]",
            }

            for download_progress in downloader.download_tracks(tracks):
                result = download_progress.result
                if result:
                    results.append(result)
                    progress.update(overall_task, completed=download_progress.current)
                    console.print(
                        f"  [{download_progress.current}/{download_progress.total}] "
                        f"{result.track.artist} - {result.track.title}: "
                        f"{status_icon[result.status]}"
                    )

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

        # Step 4: Generate M3U playlist (skip for album playlists)
        if playlist_info and not is_album_playlist(playlist_info.playlist_id):
            # Collect successful downloads (including skipped = already exists)
            m3u_tracks: list[tuple[TrackMetadata, Path]] = []
            for result in results:
                if result.status in (DownloadStatus.SUCCESS, DownloadStatus.SKIPPED):
                    if result.output_path:
                        m3u_tracks.append((result.track, result.output_path))

            if m3u_tracks:
                playlist_name = playlist_info.title or "Untitled Playlist"
                m3u_path = write_m3u(output, playlist_name, m3u_tracks)
                console.print(f"\n[cyan]M3U playlist saved:[/cyan] {m3u_path}")

    except YTMetaError as e:
        logger.error(str(e))
        raise click.ClickException(str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error")
        raise click.ClickException(f"Unexpected error: {e}") from e


if __name__ == "__main__":
    main()
