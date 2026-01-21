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
from yubal.models.domain import DownloadStatus, TrackMetadata, UnavailableTrack
from yubal.services import MetadataExtractorService, PlaylistDownloadService

logger = logging.getLogger("yubal")


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with Rich handler.

    Args:
        verbose: If True, set log level to DEBUG. Otherwise WARNING.
    """
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def print_section_header(console: Console, title: str, subtitle: str = "") -> None:
    """Print a section header with optional subtitle.

    Args:
        console: Rich console for output.
        title: Section title (will be uppercased).
        subtitle: Optional subtitle shown after the title.
    """
    header = f"  {title.upper()}"
    if subtitle:
        header += f"  [dim]│[/dim]  {subtitle}"
    console.print()
    console.rule(style="dim")
    console.print(header)
    console.rule(style="dim")


def print_track_card(console: Console, track: TrackMetadata, index: int) -> None:
    """Print a single track as a vertical card.

    Args:
        console: Rich console for output.
        track: Track metadata to display.
        index: Track index (1-based) for display.
    """
    # Format track number as "N/Total" or just "N" or empty
    if track.track_number and track.total_tracks:
        track_str = f"{track.track_number}/{track.total_tracks}"
    elif track.track_number:
        track_str = str(track.track_number)
    else:
        track_str = ""

    table = Table(
        show_header=False,
        padding=(0, 1),
        title=f"[bold yellow]Track #{index}[/bold yellow]",
        title_justify="left",
    )
    table.add_column("Field", style="bold cyan", width=12)
    table.add_column("Value", overflow="fold")

    table.add_row("Title", track.title)
    table.add_row("Artist", track.artist)
    table.add_row("Album", track.album)
    table.add_row("Album Artist", track.album_artist)
    if track_str:
        table.add_row("Track #", track_str)
    if track.year:
        table.add_row("Year", track.year)
    table.add_row("Type", track.video_type)
    if track.omv_video_id:
        table.add_row("OMV ID", track.omv_video_id)
    if track.atv_video_id:
        table.add_row("ATV ID", track.atv_video_id)
    if track.cover_url:
        table.add_row("Cover", track.cover_url)

    console.print()
    console.print(table)


def print_unavailable_tracks(
    console: Console, unavailable_tracks: list[UnavailableTrack]
) -> None:
    """Print unavailable tracks with reasons.

    Args:
        console: Rich console for output.
        unavailable_tracks: List of unavailable tracks to display.
    """
    if not unavailable_tracks:
        return
    console.print()
    console.print("[yellow]Unavailable tracks:[/yellow]")
    for ut in unavailable_tracks:
        console.print(
            f"  [dim]- {ut.title or 'Unknown'} by {ut.artist_display} "
            f"({ut.reason.value})[/dim]"
        )


def print_tracks(
    console: Console,
    tracks: list[TrackMetadata],
    skipped: int = 0,
    unavailable: int = 0,
    playlist_total: int = 0,
    kind: str | None = None,
    title: str | None = None,
    unavailable_tracks: list[UnavailableTrack] | None = None,
) -> None:
    """Print tracks as vertical cards with section header.

    Args:
        console: Rich console for output.
        tracks: List of track metadata to display.
        skipped: Number of tracks skipped (unsupported video type).
        unavailable: Number of tracks unavailable (no videoId).
        playlist_total: Total tracks in playlist (0 means no limit applied).
        kind: Content kind ("album" or "playlist").
        title: Title of the album/playlist.
        unavailable_tracks: List of unavailable tracks with reasons.
    """
    # Build subtitle with kind and title
    subtitle = ""
    if kind and title:
        subtitle = f"{kind.capitalize()}: {title}"

    print_section_header(console, "Metadata", subtitle)

    # Print each track as a vertical card
    for i, track in enumerate(tracks, 1):
        print_track_card(console, track, i)

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

    # Print unavailable tracks with details
    if unavailable_tracks:
        print_unavailable_tracks(console, unavailable_tracks)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
def main(verbose: bool) -> None:
    """Extract and download from YouTube Music albums and playlists."""
    setup_logging(verbose=verbose)


@main.command(name="meta")
@click.argument("url", metavar="URL")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--cookies",
    type=click.Path(exists=True, path_type=Path),
    help="Path to cookies.txt for YouTube Music authentication.",
)
def meta_cmd(url: str, as_json: bool, cookies: Path | None) -> None:
    """Extract structured metadata from a YouTube Music URL.

    URL should be a YouTube Music playlist URL. The content type (album vs
    playlist) is automatically detected based on the tracks.

    \b
    Examples:
      yubal meta "https://music.youtube.com/playlist?list=OLAK5uy_xxx"
      yubal meta "https://music.youtube.com/playlist?list=PLxxx"
    """
    console = Console()

    try:
        client = YTMusicClient(cookies_path=cookies)
        service = MetadataExtractorService(client)

        tracks: list[TrackMetadata] = []
        skipped = 0
        unavailable = 0
        unavailable_tracks_list: list[UnavailableTrack] = []
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
                unavailable_tracks_list = list(
                    extract_progress.playlist_info.unavailable_tracks
                )
                playlist_kind = extract_progress.playlist_info.kind.value
                playlist_title = extract_progress.playlist_info.title

        if as_json:
            data = [t.model_dump() for t in tracks]
            json.dump(data, sys.stdout, indent=2, ensure_ascii=False, default=str)
        else:
            print_tracks(
                console,
                tracks,
                skipped=skipped,
                unavailable=unavailable,
                kind=playlist_kind,
                title=playlist_title,
                unavailable_tracks=unavailable_tracks_list,
            )

    except YTMetaError as e:
        logger.error(str(e))
        raise click.ClickException(str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error")
        raise click.ClickException(f"Unexpected error: {e}") from e


@main.command(name="download")
@click.argument("url", metavar="URL")
@click.argument("output", type=click.Path(path_type=Path), metavar="OUTPUT_DIR")
@click.option(
    "--codec",
    type=click.Choice([c.value for c in AudioCodec]),
    default=AudioCodec.OPUS.value,
    help="Audio codec (default: opus).",
)
@click.option(
    "--quality",
    type=click.IntRange(0, 10),
    default=0,
    help="Audio quality, 0 (best) to 10 (worst). Only applies to lossy codecs.",
)
@click.option(
    "--max-items",
    type=int,
    default=None,
    help="Maximum number of tracks to download.",
)
@click.option(
    "--cookies",
    type=click.Path(exists=True, path_type=Path),
    help="Path to cookies.txt for YouTube Music authentication.",
)
@click.option(
    "--no-m3u",
    is_flag=True,
    help="Disable M3U playlist file generation.",
)
@click.option(
    "--no-cover",
    is_flag=True,
    help="Disable cover image saving.",
)
@click.option(
    "--album-m3u",
    is_flag=True,
    help="Generate M3U files for albums (disabled by default).",
)
def download_cmd(
    url: str,
    output: Path,
    codec: str,
    quality: int,
    max_items: int | None,
    cookies: Path | None,
    no_m3u: bool,
    no_cover: bool,
    album_m3u: bool,
) -> None:
    """Download tracks from a YouTube Music URL.

    Downloads each track using yt-dlp, preferring the ATV (Audio Track Video)
    version for better audio quality, falling back to OMV (Official Music Video)
    if ATV is unavailable. Existing files are automatically skipped.

    The content type (album vs playlist) is automatically detected based on
    the tracks. Albums skip M3U generation by default (use --album-m3u to override).

    \b
    Examples:
      yubal download "https://music.youtube.com/playlist?list=OLAK5uy_xxx" ~/Music
      yubal download "https://music.youtube.com/playlist?list=PLxxx" ~/Music
    """
    console = Console()

    try:
        # Configure the playlist download service
        config = PlaylistDownloadConfig(
            download=DownloadConfig(
                base_path=output,
                codec=AudioCodec(codec),
                quality=quality,
                quiet=True,
            ),
            generate_m3u=not no_m3u,
            save_cover=not no_cover,
            skip_album_m3u=not album_m3u,
            max_items=max_items,
        )
        service = PlaylistDownloadService(config, cookies_path=cookies)

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
        unavailable_tracks_list: list[UnavailableTrack] = []
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
                    unavailable_tracks_list = list(ep.playlist_info.unavailable_tracks)
                    playlist_total = ep.playlist_total
                    playlist_kind = ep.playlist_info.kind.value
                    playlist_title = ep.playlist_info.title

                elif p.phase == "downloading" and p.download_progress:
                    # Hide extract task, show download task on first download
                    if not progress.tasks[download_task].visible:
                        # Mark extraction complete and refresh before hiding
                        extract_total = progress.tasks[extract_task].total
                        if extract_total:
                            progress.update(extract_task, completed=extract_total)
                        progress.refresh()
                        progress.update(extract_task, visible=False)
                        progress.update(download_task, visible=True)

                        # Show tracks section
                        print_tracks(
                            console,
                            tracks,
                            skipped=skipped,
                            unavailable=unavailable,
                            unavailable_tracks=unavailable_tracks_list,
                            playlist_total=playlist_total,
                            kind=playlist_kind,
                            title=playlist_title,
                        )

                        # Show download section header
                        print_section_header(console, "Downloading", str(output))

                    dp = p.download_progress
                    progress.update(download_task, completed=dp.current, total=dp.total)
                    result = dp.result
                    status_line = (
                        f"  [{dp.current}/{dp.total}] "
                        f"{result.track.artist} - {result.track.title}: "
                        f"{status_icon[result.status]}"
                    )
                    if result.output_path:
                        status_line += f" [dim]→ {result.output_path}[/dim]"
                    console.print(status_line)

        # Get final result
        result = service.get_result()
        if not result:
            console.print("[yellow]No tracks found in playlist[/yellow]")
            # Still show unavailable tracks if any
            if unavailable_tracks_list:
                print_unavailable_tracks(console, unavailable_tracks_list)
            return

        # Show summary section
        print_section_header(console, "Summary")
        console.print(
            f"  [green]Downloaded: {result.success_count}[/green]  "
            f"[yellow]Skipped: {result.skipped_count}[/yellow]  "
            f"[red]Failed: {result.failed_count}[/red]"
        )

        # Show failed downloads
        failed = [
            r for r in result.download_results if r.status == DownloadStatus.FAILED
        ]
        if failed:
            console.print()
            console.print("  [red]Failed:[/red]")
            for r in failed:
                console.print(
                    f"    [red]• {r.track.artist} - {r.track.title}: {r.error}[/red]"
                )

        # Show generated files
        if result.m3u_path or result.cover_path:
            console.print()
            console.print("  [cyan]Output files:[/cyan]")
            if result.m3u_path:
                console.print(f"    • M3U: {result.m3u_path}")
            if result.cover_path:
                console.print(f"    • Cover: {result.cover_path}")

    except YTMetaError as e:
        logger.error(str(e))
        raise click.ClickException(str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error")
        raise click.ClickException(f"Unexpected error: {e}") from e


if __name__ == "__main__":
    main()
