"""Sync service - orchestrates download and tagging workflow."""

import shutil
import tempfile
from pathlib import Path

from yubal.core import ProgressCallback, ProgressEvent, ProgressStep, SyncResult
from yubal.services.downloader import Downloader
from yubal.services.tagger import Tagger


class SyncService:
    """Orchestrates the download → tag workflow."""

    def __init__(
        self,
        library_dir: Path,
        beets_config: Path,
        audio_format: str = "mp3",
    ):
        """
        Initialize the sync service.

        Args:
            library_dir: Directory for the organized music library
            beets_config: Path to beets configuration file
            audio_format: Audio format for downloads (mp3, m4a, opus, etc.)
        """
        self.library_dir = library_dir
        self.beets_config = beets_config
        self.audio_format = audio_format

    def sync_album(
        self,
        url: str,
        progress_callback: ProgressCallback | None = None,
    ) -> SyncResult:
        """
        Download and tag an album in one operation.

        Args:
            url: YouTube Music album/playlist URL
            progress_callback: Optional callback for progress updates

        Returns:
            SyncResult with success status and details
        """
        # Create temp directory for download
        temp_dir = Path(tempfile.mkdtemp(prefix="yubal_"))

        if progress_callback:
            progress_callback(
                ProgressEvent(
                    step=ProgressStep.STARTING,
                    message=f"Starting sync from: {url}",
                    details={"temp_dir": str(temp_dir)},
                )
            )

        try:
            # Step 1: Download
            if progress_callback:
                progress_callback(
                    ProgressEvent(
                        step=ProgressStep.DOWNLOADING,
                        message="Starting download...",
                    )
                )

            downloader = Downloader(audio_format=self.audio_format)
            download_result = downloader.download_album(
                url, temp_dir, progress_callback=progress_callback
            )

            if not download_result.success:
                if progress_callback:
                    progress_callback(
                        ProgressEvent(
                            step=ProgressStep.ERROR,
                            message=download_result.error or "Download failed",
                        )
                    )
                return SyncResult(
                    success=False,
                    download_result=download_result,
                    error=download_result.error or "Download failed",
                )

            if progress_callback:
                track_count = len(download_result.downloaded_files)
                progress_callback(
                    ProgressEvent(
                        step=ProgressStep.DOWNLOADING,
                        message=f"Downloaded {track_count} tracks",
                        progress=100.0,
                        details={
                            "track_count": track_count,
                            "album": download_result.album_info.title
                            if download_result.album_info
                            else None,
                        },
                    )
                )

            # Step 2: Tag
            if progress_callback:
                progress_callback(
                    ProgressEvent(
                        step=ProgressStep.TAGGING,
                        message="Starting tagging...",
                    )
                )

            tagger = Tagger(
                beets_config=self.beets_config,
                library_dir=self.library_dir,
                beets_db=self.beets_config.parent / "beets.db",
            )
            tag_result = tagger.tag_album(
                temp_dir, progress_callback=progress_callback
            )

            if not tag_result.success:
                if progress_callback:
                    progress_callback(
                        ProgressEvent(
                            step=ProgressStep.ERROR,
                            message=tag_result.error or "Tagging failed",
                        )
                    )
                return SyncResult(
                    success=False,
                    download_result=download_result,
                    tag_result=tag_result,
                    album_info=download_result.album_info,
                    error=tag_result.error or "Tagging failed",
                )

            # Success
            if progress_callback:
                progress_callback(
                    ProgressEvent(
                        step=ProgressStep.COMPLETE,
                        message=f"Sync complete: {tag_result.dest_dir}",
                        details={
                            "destination": str(tag_result.dest_dir)
                            if tag_result.dest_dir
                            else None,
                            "track_count": tag_result.track_count,
                        },
                    )
                )

            return SyncResult(
                success=True,
                download_result=download_result,
                tag_result=tag_result,
                album_info=download_result.album_info,
                destination=tag_result.dest_dir,
            )

        finally:
            # Cleanup temp directory
            if temp_dir.exists():
                if progress_callback:
                    progress_callback(
                        ProgressEvent(
                            step=ProgressStep.COMPLETE,
                            message="Cleaning up temp directory...",
                        )
                    )
                shutil.rmtree(temp_dir, ignore_errors=True)
