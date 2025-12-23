"""Sync command."""
import shutil
import tempfile
from pathlib import Path

import typer

from app.cli.utils import (
    DEFAULT_BEETS_CONFIG,
    DEFAULT_LIBRARY_DIR,
    create_tagger,
    echo_error,
    echo_info,
    echo_success,
    validate_beets_config,
)
from app.services.downloader import Downloader


def sync(
    url: str = typer.Argument(..., help="YouTube Music album/playlist URL"),
    library_dir: Path = typer.Option(
        DEFAULT_LIBRARY_DIR,
        "--library-dir", "-l",
        help="Library directory for organized music",
    ),
    beets_config: Path = typer.Option(
        DEFAULT_BEETS_CONFIG,
        "--beets-config", "-c",
        help="Path to beets configuration file",
    ),
    audio_format: str = typer.Option(
        "mp3",
        "--format", "-f",
        help="Audio format (mp3, m4a, opus, etc.)",
    ),
) -> None:
    """
    Download and tag an album in one step.

    Combines download + tag commands: downloads from YouTube,
    then imports and organizes using beets.
    """
    validate_beets_config(beets_config)

    temp_dir = Path(tempfile.mkdtemp(prefix="ytadl_"))
    echo_info(f"Temp directory: {temp_dir}")

    try:
        # Step 1: Download
        echo_info("\n--- Step 1: Download ---")
        echo_info(f"URL: {url}")

        downloader = Downloader(audio_format=audio_format)
        download_result = downloader.download_album(url, temp_dir)

        if not download_result.success:
            echo_error(download_result.error or "Download failed")

        echo_info(f"Downloaded {len(download_result.downloaded_files)} tracks")
        if download_result.album_info:
            echo_info(
                f"Album: {download_result.album_info.title} "
                f"by {download_result.album_info.artist}"
            )

        # Step 2: Tag
        echo_info("\n--- Step 2: Tag ---")

        tagger = create_tagger(library_dir, beets_config)
        tag_result = tagger.tag_album(temp_dir)

        if not tag_result.success:
            echo_error(tag_result.error or "Tagging failed")

        echo_info(f"Tagged {tag_result.track_count} tracks")

        # Success
        echo_info("\n--- Complete ---")
        if tag_result.dest_dir:
            echo_success(f"Album saved to: {tag_result.dest_dir}")
        else:
            echo_success("Sync complete")

    finally:
        if temp_dir.exists():
            echo_info("Cleaning up temp directory...")
            shutil.rmtree(temp_dir, ignore_errors=True)
