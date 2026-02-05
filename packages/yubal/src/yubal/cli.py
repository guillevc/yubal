#!/usr/bin/env python3
"""Command-line interface for yubal.

This CLI is primarily for debugging and development.
For production use, import yubal as a library.
"""

import glob as globlib
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

import click
from mediafile import MediaFile, UnreadableFileError
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
from yubal.models.enums import DownloadStatus, SkipReason
from yubal.models.progress import ExtractProgress
from yubal.models.track import TrackMetadata, UnavailableTrack
from yubal.services import MetadataExtractorService, PlaylistDownloadService
from yubal.utils.url import is_single_track_url

logger = logging.getLogger("yubal")


@dataclass
class ExtractionState:
    """Accumulates state during metadata extraction."""

    tracks: list[TrackMetadata] = field(default_factory=list)
    skipped_by_reason: dict[SkipReason, int] = field(default_factory=dict)
    unavailable_tracks: list[UnavailableTrack] = field(default_factory=list)
    playlist_total: int = 0
    playlist_kind: str | None = None
    playlist_title: str | None = None

    @property
    def skipped(self) -> int:
        """Total skipped tracks."""
        return sum(self.skipped_by_reason.values())

    @property
    def unavailable(self) -> int:
        """Tracks without video ID."""
        return self.skipped_by_reason.get(SkipReason.NO_VIDEO_ID, 0)

    def update_from_progress(self, progress: ExtractProgress) -> None:
        """Update state from extraction progress."""
        if progress.track is not None:
            self.tracks.append(progress.track)
        self.skipped_by_reason = progress.skipped_by_reason
        self.unavailable_tracks = list(progress.playlist_info.unavailable_tracks)
        self.playlist_total = progress.playlist_total
        self.playlist_kind = progress.playlist_info.kind.value
        self.playlist_title = progress.playlist_info.title


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


# Standard progress bar columns used by both meta and download commands.
# Using the same console for Progress and RichHandler ensures logs appear
# above the progress bar rather than interfering with it.
PROGRESS_COLUMNS = (
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    TimeElapsedColumn(),
)


def setup_logging(verbose: bool = False, console: Console | None = None) -> None:
    """Configure logging with Rich handler.

    This function clears existing handlers before adding a new one, allowing
    it to be called multiple times to reconfigure logging (e.g., to switch
    from default console to a shared Progress console).

    Args:
        verbose: If True, set log level to DEBUG. Otherwise WARNING.
            When reconfiguring with a console, pass the same verbose
            setting to preserve the log level.
        console: Optional Console instance to use for RichHandler. When
            using Progress bars, pass the same Console to both Progress
            and this function so logs appear above the progress bar.
    """
    level = logging.DEBUG if verbose else logging.WARNING

    # Clear existing handlers to allow reconfiguration
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = RichHandler(
        rich_tracebacks=True,
        show_path=False,
        console=console,
    )
    handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))

    root_logger.setLevel(level)
    root_logger.addHandler(handler)


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
            f"({ut.reason.label})[/dim]"
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
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Extract and download from YouTube Music albums and playlists."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    setup_logging(verbose=verbose)


@main.command(name="meta")
@click.argument("url", metavar="URL")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--cookies",
    type=click.Path(exists=True, path_type=Path),
    help="Path to cookies.txt for YouTube Music authentication.",
)
@click.pass_context
def meta_cmd(ctx: click.Context, url: str, as_json: bool, cookies: Path | None) -> None:
    """Extract structured metadata from a YouTube Music URL.

    URL can be either a single track URL or a playlist/album URL.
    The content type is automatically detected.

    \b
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
        )
        service = PlaylistDownloadService(config, cookies_path=cookies)

        # Status icons for display
        status_icon = {
            DownloadStatus.SUCCESS: "[green]OK[/green]",
            DownloadStatus.SKIPPED: "[yellow]SKIP[/yellow]",
            DownloadStatus.FAILED: "[red]FAIL[/red]",
        }

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
                        f"{status_icon[result.status]}"
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


# ============================================================================
# TAGS COMMAND - Inspect audio file tags including ReplayGain
# ============================================================================

# ReplayGain/R128 field names for special highlighting
REPLAYGAIN_FIELDS = (
    "rg_track_gain",
    "rg_track_peak",
    "rg_album_gain",
    "rg_album_peak",
    "r128_track_gain",
    "r128_album_gain",
)


def format_replaygain_value(value: float | int | None, is_gain: bool = True) -> str:
    """Format a ReplayGain value for display.

    Args:
        value: The ReplayGain value (gain in dB or peak as ratio).
        is_gain: True for gain values (add dB suffix), False for peak values.

    Returns:
        Formatted string or "(not set)" for None values.
    """
    if value is None:
        return "[dim](not set)[/dim]"
    if is_gain:
        # Gain values: show sign and dB suffix
        return f"{value:+.2f} dB"
    # Peak values: show as ratio (no suffix)
    return f"{value:.6f}"


def format_r128_value(value: int | None) -> str:
    """Format an R128 gain value for display.

    R128 values are stored as Q7.8 fixed point integers.
    To convert to dB: value / 256.

    Args:
        value: The R128 gain value as integer.

    Returns:
        Formatted string showing both raw value and dB equivalent.
    """
    if value is None:
        return "[dim](not set)[/dim]"
    db_value = value / 256.0
    return f"{db_value:+.2f} dB ({value})"


def get_file_tags(path: Path) -> dict:
    """Read all tags from an audio file.

    Args:
        path: Path to the audio file.

    Returns:
        Dictionary with categorized tag data.

    Raises:
        UnreadableFileError: If the file cannot be read.
    """
    audio = MediaFile(path)

    # Basic metadata
    basic = {
        "title": audio.title,
        "artist": audio.artist,
        "artists": audio.artists,
        "album": audio.album,
        "albumartist": audio.albumartist,
        "albumartists": audio.albumartists,
        "track": audio.track,
        "tracktotal": audio.tracktotal,
        "disc": audio.disc,
        "disctotal": audio.disctotal,
        "year": audio.year,
        "date": str(audio.date) if audio.date else None,
        "original_year": audio.original_year,
        "genre": audio.genre,
        "genres": audio.genres,
    }

    # Technical info
    technical = {
        "format": audio.format,
        "bitrate": audio.bitrate,
        "bitrate_mode": audio.bitrate_mode,
        "samplerate": audio.samplerate,
        "bitdepth": audio.bitdepth,
        "channels": audio.channels,
        "length": audio.length,
        "encoder": audio.encoder,
    }

    # ReplayGain/R128 fields
    replaygain = {
        "rg_track_gain": audio.rg_track_gain,
        "rg_track_peak": audio.rg_track_peak,
        "rg_album_gain": audio.rg_album_gain,
        "rg_album_peak": audio.rg_album_peak,
        "r128_track_gain": audio.r128_track_gain,
        "r128_album_gain": audio.r128_album_gain,
    }

    # Image info
    images = {"count": len(audio.images) if audio.images else 0}

    return {
        "path": str(path),
        "basic": basic,
        "technical": technical,
        "replaygain": replaygain,
        "images": images,
    }


def format_duration(seconds: float | None) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted duration string.
    """
    if seconds is None:
        return "[dim](unknown)[/dim]"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_bitrate(bitrate: float | int | None) -> str:
    """Format bitrate for display.

    The mediafile library returns bitrate in different units depending on format.
    We normalize to kbps for display.

    Args:
        bitrate: Bitrate value from mediafile.

    Returns:
        Formatted bitrate string in kbps.
    """
    if bitrate is None:
        return "[dim](unknown)[/dim]"
    # If bitrate > 10000, it's likely in bps (e.g., WAVE files)
    # Convert to kbps for consistent display
    if bitrate > 10000:
        bitrate = bitrate / 1000
    return f"{int(bitrate)} kbps"


def format_samplerate(hz: int | None) -> str:
    """Format sample rate in Hz.

    Args:
        hz: Sample rate in Hz.

    Returns:
        Formatted sample rate string.
    """
    if hz is None:
        return "[dim](unknown)[/dim]"
    return f"{hz} Hz"


def print_tag_card(console: Console, tags: dict) -> None:
    """Print a single file's tags as a vertical card.

    Args:
        console: Rich console for output.
        tags: Tag data dictionary from get_file_tags().
    """
    path = Path(tags["path"])

    # Header with file path
    print_section_header(console, "TAGS", str(path))

    # Basic metadata table
    basic = tags["basic"]
    basic_table = Table(
        show_header=False,
        padding=(0, 1),
        title="[bold cyan]Basic Metadata[/bold cyan]",
        title_justify="left",
        box=None,
    )
    basic_table.add_column("Field", style="bold", width=14)
    basic_table.add_column("Value", overflow="fold")

    if basic["title"]:
        basic_table.add_row("Title", basic["title"])
    if basic["artist"]:
        basic_table.add_row("Artist", basic["artist"])
    if basic["artists"] and len(basic["artists"]) > 1:
        basic_table.add_row("Artists", " / ".join(basic["artists"]))
    if basic["album"]:
        basic_table.add_row("Album", basic["album"])
    if basic["albumartist"]:
        basic_table.add_row("Album Artist", basic["albumartist"])
    if basic["track"] or basic["tracktotal"]:
        track_str = str(basic["track"] or "?")
        if basic["tracktotal"]:
            track_str += f"/{basic['tracktotal']}"
        basic_table.add_row("Track", track_str)
    if basic["disc"] or basic["disctotal"]:
        disc_str = str(basic["disc"] or "?")
        if basic["disctotal"]:
            disc_str += f"/{basic['disctotal']}"
        basic_table.add_row("Disc", disc_str)
    if basic["year"]:
        basic_table.add_row("Year", str(basic["year"]))
    if basic["genre"]:
        basic_table.add_row("Genre", basic["genre"])
    if basic["genres"] and len(basic["genres"]) > 1:
        basic_table.add_row("Genres", " / ".join(basic["genres"]))

    console.print()
    console.print(basic_table)

    # Technical info table
    tech = tags["technical"]
    tech_table = Table(
        show_header=False,
        padding=(0, 1),
        title="[bold cyan]Technical[/bold cyan]",
        title_justify="left",
        box=None,
    )
    tech_table.add_column("Field", style="bold", width=14)
    tech_table.add_column("Value", overflow="fold")

    if tech["format"]:
        tech_table.add_row("Format", tech["format"])
    tech_table.add_row("Duration", format_duration(tech["length"]))
    tech_table.add_row("Bitrate", format_bitrate(tech["bitrate"]))
    if tech["bitrate_mode"]:
        tech_table.add_row("Bitrate Mode", tech["bitrate_mode"])
    tech_table.add_row("Sample Rate", format_samplerate(tech["samplerate"]))
    if tech["bitdepth"]:
        tech_table.add_row("Bit Depth", f"{tech['bitdepth']} bit")
    if tech["channels"]:
        ch = tech["channels"]
        ch_str = "Mono" if ch == 1 else "Stereo" if ch == 2 else f"{ch} channels"
        tech_table.add_row("Channels", ch_str)
    if tech["encoder"]:
        tech_table.add_row("Encoder", tech["encoder"])

    console.print()
    console.print(tech_table)

    # ReplayGain table
    rg = tags["replaygain"]
    rg_table = Table(
        show_header=False,
        padding=(0, 1),
        title="[bold yellow]ReplayGain[/bold yellow]",
        title_justify="left",
        box=None,
    )
    rg_table.add_column("Field", style="bold", width=14)
    rg_table.add_column("Value", overflow="fold")

    rg_table.add_row("Track Gain", format_replaygain_value(rg["rg_track_gain"], True))
    rg_table.add_row("Track Peak", format_replaygain_value(rg["rg_track_peak"], False))
    rg_table.add_row("Album Gain", format_replaygain_value(rg["rg_album_gain"], True))
    rg_table.add_row("Album Peak", format_replaygain_value(rg["rg_album_peak"], False))
    rg_table.add_row("R128 Track", format_r128_value(rg["r128_track_gain"]))
    rg_table.add_row("R128 Album", format_r128_value(rg["r128_album_gain"]))

    console.print()
    console.print(rg_table)

    # Images info
    img_count = tags["images"]["count"]
    console.print()
    if img_count:
        console.print(f"[bold]Embedded Images:[/bold] {img_count}")
    else:
        console.print("[bold]Embedded Images:[/bold] [dim](none)[/dim]")


def print_replaygain_table(console: Console, files_tags: list[dict]) -> None:
    """Print a horizontal table showing ReplayGain info for multiple files.

    Args:
        console: Rich console for output.
        files_tags: List of tag data dictionaries from get_file_tags().
    """
    table = Table(title="ReplayGain Tags", show_lines=True)
    table.add_column("File", style="cyan", max_width=40)
    table.add_column("Track Gain", justify="right")
    table.add_column("Track Peak", justify="right")
    table.add_column("Album Gain", justify="right")
    table.add_column("Album Peak", justify="right")
    table.add_column("R128 Track", justify="right")
    table.add_column("R128 Album", justify="right")

    for tags in files_tags:
        path = Path(tags["path"])
        rg = tags["replaygain"]
        table.add_row(
            path.name,
            format_replaygain_value(rg["rg_track_gain"], True),
            format_replaygain_value(rg["rg_track_peak"], False),
            format_replaygain_value(rg["rg_album_gain"], True),
            format_replaygain_value(rg["rg_album_peak"], False),
            format_r128_value(rg["r128_track_gain"]),
            format_r128_value(rg["r128_album_gain"]),
        )

    console.print()
    console.print(table)


def expand_file_patterns(patterns: tuple[str, ...]) -> list[Path]:
    """Expand file patterns (including globs) to a list of paths.

    Args:
        patterns: Tuple of file paths or glob patterns.

    Returns:
        List of resolved file paths.
    """
    files: list[Path] = []
    for pattern in patterns:
        # Check if it's a glob pattern
        if "*" in pattern or "?" in pattern or "[" in pattern:
            matches = globlib.glob(pattern, recursive=True)
            files.extend(Path(m) for m in sorted(matches) if Path(m).is_file())
        else:
            path = Path(pattern)
            if path.is_file():
                files.append(path)
            elif path.is_dir():
                # If a directory is given, find all audio files in it
                for ext in ("*.mp3", "*.flac", "*.m4a", "*.opus", "*.ogg", "*.wav"):
                    files.extend(sorted(path.glob(ext)))
    return files


@main.command(name="tags")
@click.argument("files", nargs=-1, required=True, metavar="FILE...")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.option(
    "-r",
    "--replaygain-only",
    is_flag=True,
    help="Show only ReplayGain/R128 fields in table format.",
)
@click.pass_context
def tags_cmd(
    ctx: click.Context,
    files: tuple[str, ...],
    as_json: bool,
    replaygain_only: bool,
) -> None:
    """Inspect audio file tags including ReplayGain metadata.

    Display metadata tags from audio files, with special highlighting for
    ReplayGain and R128 loudness normalization fields. Useful for comparing
    files before and after applying ReplayGain with tools like rsgain.

    FILE can be a path to an audio file, a glob pattern, or a directory.
    Supports MP3, FLAC, M4A, Opus, OGG, and WAV files.

    \b
    Examples:
      yubal tags ~/Music/Artist/Album/track.opus
      yubal tags ~/Music/Artist/Album/*.opus
      yubal tags ~/Music/Artist/Album/ -r
      yubal tags track1.opus track2.opus --json
    """
    console = Console()

    # Expand file patterns
    file_paths = expand_file_patterns(files)

    if not file_paths:
        raise click.ClickException("No files found matching the given patterns.")

    # Read tags from all files
    all_tags: list[dict] = []
    errors: list[tuple[Path, str]] = []

    for path in file_paths:
        try:
            tags = get_file_tags(path)
            all_tags.append(tags)
        except UnreadableFileError as e:
            errors.append((path, str(e)))
        except Exception as e:
            errors.append((path, f"Unexpected error: {e}"))

    # Output results
    if as_json:
        json.dump(all_tags, sys.stdout, indent=2, ensure_ascii=False, default=str)
        sys.stdout.write("\n")
    elif replaygain_only:
        # Horizontal table for ReplayGain comparison
        if all_tags:
            print_replaygain_table(console, all_tags)
    elif len(all_tags) == 1:
        # Single file: vertical card format
        print_tag_card(console, all_tags[0])
    else:
        # Multiple files: vertical cards for each
        for tags in all_tags:
            print_tag_card(console, tags)

    # Report errors
    if errors:
        console.print()
        console.print("[red]Errors:[/red]")
        for path, error in errors:
            console.print(f"  [red]- {path}: {error}[/red]")


if __name__ == "__main__":
    main()
