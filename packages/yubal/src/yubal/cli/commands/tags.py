"""Tags command for inspecting audio file metadata."""

import glob as globlib
import json
import sys
from pathlib import Path

import click
from mediafile import MediaFile, UnreadableFileError
from rich.console import Console
from rich.table import Table

from yubal.cli.formatting import print_section_header

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


@click.command(name="tags")
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
