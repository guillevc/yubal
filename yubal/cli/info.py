"""Info command."""

import json
import subprocess
from pathlib import Path

import typer

from yubal.cli.utils import echo_error, echo_info
from yubal.core.constants import PRIORITY_TAGS, SKIP_TAGS


def _get_audio_tags(file_path: Path) -> dict[str, str]:
    """Extract metadata tags from an audio file using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return data.get("format", {}).get("tags", {})


def _truncate_value(value: str, max_length: int = 45) -> str:
    """Truncate a string and add ellipsis if too long."""
    value = str(value).replace("\n", " ").strip()
    if len(value) > max_length:
        return value[: max_length - 3] + "..."
    return value


def _print_metadata_table(tags: dict[str, str]) -> None:
    """Print metadata tags in a formatted table."""
    rows: list[tuple[str, str]] = []
    for key in PRIORITY_TAGS:
        if key in tags:
            rows.append((key, _truncate_value(tags[key])))

    for key in sorted(tags.keys()):
        if key not in PRIORITY_TAGS and key not in SKIP_TAGS:
            rows.append((key, _truncate_value(tags[key])))

    tag_width = max((len(r[0]) for r in rows), default=3)
    val_width = max((len(r[1]) for r in rows), default=5)

    bold_offset = 8
    color_offset = 9

    echo_info("")
    header_tag = typer.style("Tag", bold=True)
    header_val = typer.style("Value", bold=True)
    tag_w = tag_width + bold_offset
    val_w = val_width + bold_offset
    typer.echo(f"| {header_tag:<{tag_w}} | {header_val:<{val_w}} |")
    echo_info(f"|{'-' * (tag_width + 2)}|{'-' * (val_width + 2)}|")

    for key, value in rows:
        styled_key = typer.style(key, fg=typer.colors.CYAN)
        typer.echo(
            f"| {styled_key:<{tag_width + color_offset}} | {value:<{val_width}} |"
        )


def info(
    file_path: Path = typer.Argument(..., help="Audio file to inspect"),
) -> None:
    """
    Display metadata tags of an audio file.

    Shows embedded ID3/Vorbis tags in a table format.
    """
    if not file_path.exists():
        echo_error(f"File not found: {file_path}")

    try:
        tags = _get_audio_tags(file_path)
        if not tags:
            echo_info("No metadata tags found.")
            return
        _print_metadata_table(tags)
    except subprocess.CalledProcessError:
        echo_error("ffprobe failed. Is ffmpeg installed?")
    except json.JSONDecodeError:
        echo_error("Failed to parse ffprobe output")
