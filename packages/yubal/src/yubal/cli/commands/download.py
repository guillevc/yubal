"""Download command for YouTube Music tracks."""

import logging
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress

from yubal.cli.commands.meta import print_no_tracks_message
from yubal.cli.formatting import (
    PROGRESS_COLUMNS,
    print_section_header,
    print_tracks,
)
from yubal.cli.logging import setup_logging
from yubal.cli.state import ExtractionState
from yubal.config import AudioCodec, DownloadConfig, PlaylistDownloadConfig
from yubal.exceptions import YTMetaError
from yubal.models.enums import DownloadStatus
from yubal.services import PlaylistDownloadService
from yubal.utils.url import is_single_track_url

logger = logging.getLogger("yubal")

# Status icons for display
STATUS_ICON = {
    DownloadStatus.SUCCESS: "[green]OK[/green]",
    DownloadStatus.SKIPPED: "[yellow]SKIP[/yellow]",
    DownloadStatus.FAILED: "[red]FAIL[/red]",
}


@click.command(name="download")
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
@click.option(
    "--no-replaygain",
    is_flag=True,
    help="Disable ReplayGain tagging.",
)
@click.pass_context
def download_cmd(
    ctx: click.Context,
    url: str,
    output: Path,
    codec: str,
    quality: int,
    max_items: int | None,
    cookies: Path | None,
    no_m3u: bool,
    no_cover: bool,
    album_m3u: bool,
    no_replaygain: bool,
) -> None:
    """Download tracks from a YouTube Music URL.

    URL can be either a single track URL or a playlist/album URL.
    Downloads each track using yt-dlp, preferring the ATV (Audio Track Video)
    version for better audio quality, falling back to OMV (Official Music Video)
    if ATV is unavailable. Existing files are automatically skipped.

    The content type (album, playlist, or single track) is automatically detected.
    Albums skip M3U generation by default (use --album-m3u to override).

    \b
    Examples:
      yubal download "https://music.youtube.com/watch?v=VIDEO_ID" ~/Music
      yubal download "https://music.youtube.com/playlist?list=OLAK5uy_xxx" ~/Music
      yubal download "https://music.youtube.com/playlist?list=PLxxx" ~/Music
    """
    console = Console()
    verbose = ctx.obj.get("verbose", False)

    # Reconfigure logging to use this console so logs appear above progress bar
    setup_logging(verbose=verbose, console=console)

    try:
        # Detect single track URL and inform the user
        if is_single_track_url(url):
            console.print("[cyan]Detected single track[/cyan]")
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
            apply_replaygain=not no_replaygain,
        )
        service = PlaylistDownloadService(config, cookies_path=cookies)

        state = ExtractionState()

        with Progress(*PROGRESS_COLUMNS, console=console) as progress:
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
                    state.update_from_progress(ep)

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
                            state.tracks,
                            skipped=state.skipped,
                            unavailable=state.unavailable,
                            unavailable_tracks=state.unavailable_tracks,
                            playlist_total=state.playlist_total,
                            kind=state.playlist_kind,
                            title=state.playlist_title,
                        )

                        # Show download section header
                        print_section_header(console, "Downloading", str(output))

                    dp = p.download_progress
                    progress.update(download_task, completed=dp.current, total=dp.total)
                    result = dp.result
                    status_line = (
                        f"  [{dp.current}/{dp.total}] "
                        f"{result.track.artist} - {result.track.title}: "
                        f"{STATUS_ICON[result.status]}"
                    )
                    if result.output_path:
                        status_line += f" [dim]→ {result.output_path}[/dim]"
                    console.print(status_line)

        # Get final result
        final_result = service.get_result()
        if not final_result:
            print_no_tracks_message(console, state)
            return

        # Show summary section
        print_section_header(console, "Summary")
        console.print(
            f"  [green]Downloaded: {final_result.success_count}[/green]  "
            f"[yellow]Skipped: {final_result.skipped_count}[/yellow]  "
            f"[red]Failed: {final_result.failed_count}[/red]"
        )

        # Show failed downloads
        failed = [
            r
            for r in final_result.download_results
            if r.status == DownloadStatus.FAILED
        ]
        if failed:
            console.print()
            console.print("  [red]Failed:[/red]")
            for r in failed:
                console.print(
                    f"    [red]• {r.track.artist} - {r.track.title}: {r.error}[/red]"
                )

        # Show generated files
        if final_result.m3u_path or final_result.cover_path:
            console.print()
            console.print("  [cyan]Output files:[/cyan]")
            if final_result.m3u_path:
                console.print(f"    • M3U: {final_result.m3u_path}")
            if final_result.cover_path:
                console.print(f"    • Cover: {final_result.cover_path}")

    except YTMetaError as e:
        logger.error(str(e))
        raise click.ClickException(str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error")
        raise click.ClickException(f"Unexpected error: {e}") from e
