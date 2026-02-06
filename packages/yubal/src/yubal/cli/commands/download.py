"""Download command for YouTube Music tracks."""

import logging
from pathlib import Path
from typing import Annotated

import typer
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


def download_cmd(
    ctx: typer.Context,
    url: Annotated[str, typer.Argument(metavar="URL")],
    output: Annotated[Path, typer.Argument(metavar="OUTPUT_DIR")],
    codec: Annotated[
        AudioCodec,
        typer.Option(help="Audio codec (default: opus)."),
    ] = AudioCodec.OPUS,
    quality: Annotated[
        int,
        typer.Option(
            min=0,
            max=10,
            help="Audio quality, 0 (best) to 10 (worst). Only applies to lossy codecs.",
        ),
    ] = 0,
    max_items: Annotated[
        int | None,
        typer.Option(help="Maximum number of tracks to download."),
    ] = None,
    cookies: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            file_okay=True,
            dir_okay=False,
            help="Path to cookies.txt for YouTube Music authentication.",
        ),
    ] = None,
    no_m3u: Annotated[
        bool,
        typer.Option("--no-m3u", help="Disable M3U playlist file generation."),
    ] = False,
    no_cover: Annotated[
        bool,
        typer.Option("--no-cover", help="Disable cover image saving."),
    ] = False,
    album_m3u: Annotated[
        bool,
        typer.Option(
            "--album-m3u", help="Generate M3U files for albums (disabled by default)."
        ),
    ] = False,
    no_replaygain: Annotated[
        bool,
        typer.Option("--no-replaygain", help="Disable ReplayGain tagging."),
    ] = False,
) -> None:
    """Download tracks from a YouTube Music URL.

    URL can be either a single track URL or a playlist/album URL.
    Downloads each track using yt-dlp, preferring the ATV (Audio Track Video)
    version for better audio quality, falling back to OMV (Official Music Video)
    if ATV is unavailable. Existing files are automatically skipped.

    The content type (album, playlist, or single track) is automatically detected.
    Albums skip M3U generation by default (use --album-m3u to override).

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
                codec=codec,
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
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1) from e
