"""Download command."""

from pathlib import Path

import typer

from yubal.cli.utils import echo_error, echo_info, echo_success
from yubal.services.downloader import Downloader


def download(
    url: str = typer.Argument(..., help="YouTube Music album/playlist URL"),
    output_dir: Path = typer.Option(
        ...,
        "--output-dir",
        "-o",
        help="Directory to save downloaded files",
    ),
    audio_format: str = typer.Option(
        "mp3",
        "--format",
        "-f",
        help="Audio format (mp3, m4a, opus, etc.)",
    ),
) -> None:
    """
    Download an album/playlist from YouTube Music.

    Downloads all tracks, embeds metadata, and saves to the specified directory.
    """
    echo_info(f"Downloading from: {url}")
    echo_info(f"Output directory: {output_dir}")

    downloader = Downloader(audio_format=audio_format)

    result = downloader.download_album(url, output_dir)

    if not result.success:
        echo_error(result.error or "Download failed")

    echo_info(f"Downloaded {len(result.downloaded_files)} tracks:")
    for f in sorted(result.downloaded_files):
        echo_info(f"  - {Path(f).name}")

    if result.album_info:
        echo_success(
            f"Album: {result.album_info.title} by {result.album_info.artist} "
            f"({result.album_info.track_count} tracks)"
        )
