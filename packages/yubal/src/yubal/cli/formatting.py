"""Display formatting utilities for CLI commands."""

from rich.console import Console
from rich.progress import (
    BarColumn,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from yubal.models.track import TrackMetadata, UnavailableTrack

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
