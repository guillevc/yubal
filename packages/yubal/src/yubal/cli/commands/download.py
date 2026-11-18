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
from yubal.exceptions import YubalError
from yubal.models.enums import DownloadStatus
from yubal.models.results import PlaylistDownloadResult
from yubal.services import PlaylistDownloadService
from yubal.utils.url import is_single_track_url

logger = logging.getLogger("yubal")

# Status icons for display
STATUS_ICON = {
    DownloadStatus.SUCCESS: "[green]OK[/green]",
    DownloadStatus.SKIPPED: "[yellow]SKIP[/yellow]",
    DownloadStatus.FAILED: "[red]FAIL[/red]",
}

# Shared download options (also used by the `artist` command)
CodecOpt = Annotated[
    AudioCodec,
    typer.Option(help="Audio codec (default: opus)."),
]
QualityOpt = Annotated[
    int,
    typer.Option(
        min=0,
        max=10,
        help="Audio quality, 0 (best) to 10 (worst). Only applies to lossy codecs.",
    ),
]
MaxItemsOpt = Annotated[
    int | None,
    typer.Option(help="Maximum number of tracks to download."),
]
CookiesOpt = Annotated[
    Path | None,
    typer.Option(
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Path to cookies.txt for YouTube Music authentication.",
    ),
]
NoM3uOpt = Annotated[
    bool,
    typer.Option("--no-m3u", help="Disable M3U playlist file generation."),
]
NoCoverOpt = Annotated[
    bool,
    typer.Option("--no-cover", help="Disable cover image saving."),
]
NoReplayGainOpt = Annotated[
    bool,
    typer.Option("--no-replaygain", help="Disable ReplayGain tagging."),
]
AsciiFilenamesOpt = Annotated[
    bool,
    typer.Option(
        "--ascii-filenames",
        help="Transliterate unicode to ASCII in filenames.",
    ),
]


def build_playlist_service(
    *,
    output: Path,
    codec: AudioCodec,
    quality: int,
    max_items: int | None,
    cookies: Path | None,
    no_m3u: bool,
    no_cover: bool,
    no_replaygain: bool,
    ascii_filenames: bool,
) -> PlaylistDownloadService:
    """Create a PlaylistDownloadService from CLI options."""
    config = PlaylistDownloadConfig(
        download=DownloadConfig(
            base_path=output,
            codec=codec,
            quality=quality,
            quiet=True,
            ascii_filenames=ascii_filenames,
        ),
        generate_m3u=not no_m3u,
        save_cover=not no_cover,
        max_items=max_items,
        apply_replaygain=not no_replaygain,
    )
    return PlaylistDownloadService(config, cookies_path=cookies)


def run_playlist_download(
    console: Console,
    service: PlaylistDownloadService,
    url: str,
    output: Path,
) -> PlaylistDownloadResult | None:
    """Download one URL with progress bars and a per-release summary.

    Args:
        console: Rich console for output.
        service: Configured playlist download service.
        url: YouTube Music URL (track, album, or playlist).
        output: Output directory (for display only).

    Returns:
        The download result, or None if no tracks were found.

    Raises:
        YubalError: If extraction or download fails.
    """
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
        return None

    print_download_summary(console, final_result)
    return final_result


def print_download_summary(console: Console, result: PlaylistDownloadResult) -> None:
    """Print counts, failures, and generated files for one download."""
    print_section_header(console, "Summary")
    console.print(
        f"  [green]Downloaded: {result.success_count}[/green]  "
        f"[yellow]Skipped: {result.skipped_count}[/yellow]  "
        f"[red]Failed: {result.failed_count}[/red]"
    )

    # Show failed downloads
    failed = [r for r in result.download_results if r.status == DownloadStatus.FAILED]
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


def download_cmd(
    ctx: typer.Context,
    url: Annotated[str, typer.Argument(metavar="URL")],
    output: Annotated[Path, typer.Argument(metavar="OUTPUT_DIR")],
    codec: CodecOpt = AudioCodec.OPUS,
    quality: QualityOpt = 0,
    max_items: MaxItemsOpt = None,
    cookies: CookiesOpt = None,
    no_m3u: NoM3uOpt = False,
    no_cover: NoCoverOpt = False,
    no_replaygain: NoReplayGainOpt = False,
    ascii_filenames: AsciiFilenamesOpt = False,
) -> None:
    """Download tracks from a YouTube Music URL.

    URL can be either a single track URL or a playlist/album URL.
    Downloads each track using yt-dlp, preferring the ATV (Audio Track Video)
    version for better audio quality, falling back to OMV (Official Music Video)
    if ATV is unavailable. Existing files are automatically skipped.

    The content type (album, playlist, or single track) is automatically detected.
    Albums skip M3U generation automatically.

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
        service = build_playlist_service(
            output=output,
            codec=codec,
            quality=quality,
            max_items=max_items,
            cookies=cookies,
            no_m3u=no_m3u,
            no_cover=no_cover,
            no_replaygain=no_replaygain,
            ascii_filenames=ascii_filenames,
        )
        run_playlist_download(console, service, url, output)

    except YubalError as e:
        logger.error(str(e))
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from e
    except Exception as e:
        logger.exception("Unexpected error")
        console.print(f"[red]Unexpected error: {e}[/red]")
        raise typer.Exit(code=1) from e
