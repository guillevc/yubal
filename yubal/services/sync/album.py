"""Album sync service for downloading and tagging albums."""

import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from yubal.core.enums import ProgressStep
from yubal.core.models import AlbumInfo, DownloadResult, SyncResult
from yubal.services.downloader import Downloader
from yubal.services.sync.cancel import CancelToken
from yubal.services.sync.progress import ProgressEmitter
from yubal.services.tagger import Tagger

# Progress thresholds for album sync
ALBUM_PROGRESS_START = 0.0
ALBUM_PROGRESS_FETCH_DONE = 10.0
ALBUM_PROGRESS_DOWNLOAD_DONE = 90.0
ALBUM_PROGRESS_COMPLETE = 100.0


def _get_file_bitrate(file_path: Path) -> int | None:
    """Get actual average bitrate from audio file (calculated from size/duration)."""
    from mutagen import File as MutagenFile

    try:
        audio = MutagenFile(str(file_path))
        if not audio or not audio.info or not audio.info.length:
            return None

        file_size = file_path.stat().st_size
        duration = audio.info.length

        # Calculate actual average bitrate: (bytes * 8 bits) / seconds / 1000
        return int((file_size * 8) / duration / 1000)

    except Exception:  # noqa: S110  # Best-effort, non-critical
        pass
    return None


@dataclass
class AlbumSyncService:
    """Service for syncing albums from YouTube Music.

    Orchestrates the download -> tag workflow for album imports.
    Files are downloaded to a temp directory and then organized
    by beets into the library structure.

    Attributes:
        downloader: Service for downloading from YouTube
        tagger: Service for tagging and organizing via beets
        temp_dir: Base directory for temporary download files
    """

    downloader: Downloader
    tagger: Tagger
    temp_dir: Path

    def execute(
        self,
        url: str,
        job_id: str,
        progress: ProgressEmitter,
        cancel: CancelToken,
    ) -> SyncResult:
        """Download and tag an album in one operation.

        Progress is calculated as:
        - 0% -> 10%: Fetching info phase
        - 10% -> 90%: Download phase (proportional to tracks)
        - 90% -> 100%: Import/tagging phase

        Args:
            url: YouTube Music album/playlist URL
            job_id: Unique job identifier (used for temp directory)
            progress: Emitter for progress updates
            cancel: Token for checking/signaling cancellation

        Returns:
            SyncResult with success status and details
        """
        album_info: AlbumInfo | None = None

        with self._job_temp_dir(job_id) as job_temp_dir:
            try:
                # Phase 1: Extract album info (0% -> 10%)
                progress.emit(
                    ProgressStep.FETCHING_INFO,
                    "Fetching album info...",
                    ALBUM_PROGRESS_START,
                )

                try:
                    album_info = self.downloader.extract_info(url)
                    total_tracks = album_info.track_count or 1
                except Exception as e:
                    progress.fail(f"Failed to fetch album info: {e}")
                    return SyncResult(
                        success=False,
                        error=f"Failed to fetch album info: {e}",
                    )

                progress.emit(
                    ProgressStep.FETCHING_INFO,
                    f"Found {total_tracks} tracks: {album_info.title}",
                    ALBUM_PROGRESS_FETCH_DONE,
                    {"album_info": album_info.model_dump()},
                )

                # Check cancellation before download
                if cancel.is_cancelled():
                    return SyncResult(
                        success=False,
                        album_info=album_info,
                        error="Cancelled",
                    )

                # Phase 2: Download (10% -> 90%)
                download_wrapper = progress.create_download_wrapper(
                    total_tracks,
                    ALBUM_PROGRESS_FETCH_DONE,
                    ALBUM_PROGRESS_DOWNLOAD_DONE,
                )

                progress.emit(
                    ProgressStep.DOWNLOADING,
                    "Starting download...",
                    ALBUM_PROGRESS_FETCH_DONE,
                )

                download_result = self.downloader.download_album(
                    url,
                    job_temp_dir,
                    progress_callback=download_wrapper,
                    cancel_check=cancel.is_cancelled,
                )

                # Check for failure/cancellation
                if failure := self._handle_download_result(
                    download_result, album_info, progress
                ):
                    return failure

                track_count = len(download_result.downloaded_files)
                progress.emit(
                    ProgressStep.DOWNLOADING,
                    f"Downloaded {track_count} tracks",
                    ALBUM_PROGRESS_DOWNLOAD_DONE,
                )

                # Update bitrate from actual file
                if download_result.downloaded_files and album_info:
                    real_bitrate = _get_file_bitrate(
                        Path(download_result.downloaded_files[0])
                    )
                    if real_bitrate:
                        album_info.audio_bitrate = real_bitrate

                # Phase 3: Import/Tag (90% -> 100%)
                progress.emit(
                    ProgressStep.IMPORTING,
                    "Starting import...",
                    ALBUM_PROGRESS_DOWNLOAD_DONE,
                )

                audio_files = [Path(f) for f in download_result.downloaded_files]
                tag_result = self.tagger.tag_album(audio_files, progress_callback=None)

                if not tag_result.success:
                    progress.fail(tag_result.error or "Import failed")
                    return SyncResult(
                        success=False,
                        download_result=download_result,
                        tag_result=tag_result,
                        album_info=album_info,
                        error=tag_result.error or "Import failed",
                    )

                progress.complete(
                    f"Sync complete: {tag_result.dest_dir}",
                    tag_result.dest_dir or "",
                )

                return SyncResult(
                    success=True,
                    download_result=download_result,
                    tag_result=tag_result,
                    album_info=album_info,
                    destination=tag_result.dest_dir,
                )

            except Exception as e:
                progress.fail(str(e))
                return SyncResult(
                    success=False,
                    album_info=album_info,
                    error=str(e),
                )

    @contextmanager
    def _job_temp_dir(self, job_id: str) -> Iterator[Path]:
        """Context manager for job temporary directory with automatic cleanup."""
        job_temp_dir = self.temp_dir / job_id
        job_temp_dir.mkdir(parents=True, exist_ok=True)
        try:
            yield job_temp_dir
        finally:
            if job_temp_dir.exists():
                shutil.rmtree(job_temp_dir, ignore_errors=True)

    def _handle_download_result(
        self,
        download_result: DownloadResult,
        album_info: AlbumInfo | None,
        progress: ProgressEmitter,
    ) -> SyncResult | None:
        """Check download result and return SyncResult if failed/cancelled.

        Returns None if download succeeded and processing should continue.
        """
        if download_result.cancelled:
            return SyncResult(
                success=False,
                download_result=download_result,
                album_info=album_info,
                error="Download cancelled",
            )

        if not download_result.success:
            progress.fail(download_result.error or "Download failed")
            return SyncResult(
                success=False,
                download_result=download_result,
                album_info=album_info,
                error=download_result.error or "Download failed",
            )

        return None
