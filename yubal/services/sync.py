import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from loguru import logger
from mutagen import File as MutagenFile

from yubal.core.callbacks import CancelCheck, ProgressCallback, ProgressEvent
from yubal.core.enums import ProgressStep
from yubal.core.models import AlbumInfo, DownloadResult, SyncResult
from yubal.core.utils import extract_playlist_id
from yubal.services.downloader import Downloader
from yubal.services.m3u_generator import generate_m3u, sanitize_filename
from yubal.services.metadata_enricher import MetadataEnricher, PlaylistMetadata
from yubal.services.metadata_patcher import MetadataPatcher
from yubal.services.tagger import Tagger

# Progress thresholds for album sync
ALBUM_PROGRESS_START = 0.0
ALBUM_PROGRESS_FETCH_DONE = 10.0
ALBUM_PROGRESS_DOWNLOAD_DONE = 90.0
ALBUM_PROGRESS_COMPLETE = 100.0

# Progress thresholds for playlist sync
PLAYLIST_PROGRESS_START = 0.0
PLAYLIST_PROGRESS_FETCH_DONE = 10.0
PLAYLIST_PROGRESS_DOWNLOAD_DONE = 60.0
PLAYLIST_PROGRESS_PATCH_DONE = 70.0
PLAYLIST_PROGRESS_ORGANIZE_DONE = 75.0
PLAYLIST_PROGRESS_BEETS_DONE = 90.0
PLAYLIST_PROGRESS_COMPLETE = 100.0


def _get_file_bitrate(file_path: Path) -> int | None:
    """Get actual average bitrate from audio file (calculated from size/duration)."""
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


class SyncService:
    """Orchestrates the download → tag workflow."""

    def __init__(
        self,
        library_dir: Path,
        beets_config: Path,
        audio_format: str,
        temp_dir: Path,
        playlists_dir: Path,
        downloader: Downloader,
        tagger: Tagger,
    ):
        """
        Initialize the sync service.

        Args:
            library_dir: Directory for the organized music library
            beets_config: Path to beets configuration file
            audio_format: Audio format for downloads (mp3, m4a, opus, etc.)
            temp_dir: Directory for temporary download files
            playlists_dir: Directory for playlist downloads (Playlists/{name}/)
            downloader: Downloader instance for fetching from YouTube
            tagger: Tagger instance for organizing with beets
        """
        self.library_dir = library_dir
        self.beets_config = beets_config
        self.audio_format = audio_format
        self.temp_dir = temp_dir
        self.playlists_dir = playlists_dir
        self._downloader = downloader
        self._tagger = tagger

    def _emit_progress(
        self,
        callback: ProgressCallback | None,
        step: ProgressStep,
        message: str,
        progress: float | None = None,
        details: dict[str, object] | None = None,
    ) -> None:
        """Emit a progress event if callback is provided."""
        if callback:
            event_kwargs: dict[str, object] = {
                "step": step,
                "message": message,
            }
            if progress is not None:
                event_kwargs["progress"] = progress
            if details is not None:
                event_kwargs["details"] = details
            callback(ProgressEvent(**event_kwargs))  # type: ignore[arg-type]

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

    def _create_download_progress_wrapper(
        self,
        progress_callback: ProgressCallback | None,
        total_tracks: int,
        fetch_done_progress: float,
        download_done_progress: float,
    ) -> ProgressCallback | None:
        """Create a progress wrapper that maps track progress to overall progress."""
        if not progress_callback:
            return None

        download_range = download_done_progress - fetch_done_progress

        def wrapper(event: ProgressEvent) -> None:
            if event.progress is None:
                progress_callback(event)
                return

            track_idx = event.details.get("track_index", 0) if event.details else 0
            track_progress = event.progress

            overall = (
                fetch_done_progress
                + ((track_idx + track_progress / 100) / total_tracks) * download_range
            )
            progress_callback(
                ProgressEvent(
                    step=ProgressStep.DOWNLOADING,
                    message=event.message,
                    progress=overall,
                )
            )

        return wrapper

    def _handle_download_result(
        self,
        download_result: DownloadResult,
        album_info: AlbumInfo | None,
        progress_callback: ProgressCallback | None,
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
            self._emit_progress(
                progress_callback,
                ProgressStep.FAILED,
                download_result.error or "Download failed",
            )
            return SyncResult(
                success=False,
                download_result=download_result,
                album_info=album_info,
                error=download_result.error or "Download failed",
            )

        return None

    def sync_album(
        self,
        url: str,
        job_id: str,
        progress_callback: ProgressCallback | None = None,
        cancel_check: CancelCheck | None = None,
    ) -> SyncResult:
        """
        Download and tag an album in one operation.

        Progress is calculated as:
        - 0% → 10%: Fetching info phase
        - 10% → 90%: Download phase (proportional to tracks)
        - 90% → 100%: Import/tagging phase

        Args:
            url: YouTube Music album/playlist URL
            job_id: Unique job identifier (used for temp directory)
            progress_callback: Optional callback for progress updates
            cancel_check: Function returning True if operation should cancel

        Returns:
            SyncResult with success status and details
        """
        album_info: AlbumInfo | None = None

        with self._job_temp_dir(job_id) as job_temp_dir:
            try:
                # Phase 1: Extract album info (0% → 10%)
                self._emit_progress(
                    progress_callback,
                    ProgressStep.FETCHING_INFO,
                    "Fetching album info...",
                    ALBUM_PROGRESS_START,
                )

                try:
                    album_info = self._downloader.extract_info(url)
                    total_tracks = album_info.track_count or 1
                except Exception as e:
                    self._emit_progress(
                        progress_callback,
                        ProgressStep.FAILED,
                        f"Failed to fetch album info: {e}",
                    )
                    return SyncResult(
                        success=False,
                        error=f"Failed to fetch album info: {e}",
                    )

                self._emit_progress(
                    progress_callback,
                    ProgressStep.FETCHING_INFO,
                    f"Found {total_tracks} tracks: {album_info.title}",
                    ALBUM_PROGRESS_FETCH_DONE,
                    {"album_info": album_info.model_dump()},
                )

                # Phase 2: Download (10% → 90%)
                download_wrapper = self._create_download_progress_wrapper(
                    progress_callback,
                    total_tracks,
                    ALBUM_PROGRESS_FETCH_DONE,
                    ALBUM_PROGRESS_DOWNLOAD_DONE,
                )

                self._emit_progress(
                    progress_callback,
                    ProgressStep.DOWNLOADING,
                    "Starting download...",
                    ALBUM_PROGRESS_FETCH_DONE,
                )

                download_result = self._downloader.download_album(
                    url,
                    job_temp_dir,
                    progress_callback=download_wrapper,
                    cancel_check=cancel_check,
                )

                # Check for failure/cancellation
                if failure := self._handle_download_result(
                    download_result, album_info, progress_callback
                ):
                    return failure

                track_count = len(download_result.downloaded_files)
                self._emit_progress(
                    progress_callback,
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

                # Phase 3: Import/Tag (90% → 100%)
                self._emit_progress(
                    progress_callback,
                    ProgressStep.IMPORTING,
                    "Starting import...",
                    ALBUM_PROGRESS_DOWNLOAD_DONE,
                )

                audio_files = [Path(f) for f in download_result.downloaded_files]
                tag_result = self._tagger.tag_album(
                    audio_files, progress_callback=progress_callback
                )

                if not tag_result.success:
                    self._emit_progress(
                        progress_callback,
                        ProgressStep.FAILED,
                        tag_result.error or "Import failed",
                    )
                    return SyncResult(
                        success=False,
                        download_result=download_result,
                        tag_result=tag_result,
                        album_info=album_info,
                        error=tag_result.error or "Import failed",
                    )

                self._emit_progress(
                    progress_callback,
                    ProgressStep.COMPLETED,
                    f"Sync complete: {tag_result.dest_dir}",
                    ALBUM_PROGRESS_COMPLETE,
                )

                return SyncResult(
                    success=True,
                    download_result=download_result,
                    tag_result=tag_result,
                    album_info=album_info,
                    destination=tag_result.dest_dir,
                )

            except Exception as e:
                self._emit_progress(progress_callback, ProgressStep.FAILED, str(e))
                return SyncResult(
                    success=False,
                    album_info=album_info,
                    error=str(e),
                )

    def sync_playlist(
        self,
        url: str,
        job_id: str,
        progress_callback: ProgressCallback | None = None,
        cancel_check: CancelCheck | None = None,
    ) -> SyncResult:
        """
        Download and organize a playlist with metadata enrichment.

        Progress phases:
        - 0% → 10%: Enriching metadata via ytmusicapi
        - 10% → 60%: Downloading tracks via yt-dlp
        - 60% → 70%: Patching metadata with enriched data
        - 70% → 75%: Organizing files to Playlists/{name}/
        - 75% → 90%: Beets import (in place, no moves)
        - 90% → 100%: Generating M3U playlist

        Args:
            url: YouTube Music playlist URL
            job_id: Unique job identifier (used for temp directory)
            progress_callback: Optional callback for progress updates
            cancel_check: Function returning True if operation should cancel

        Returns:
            SyncResult with success status and details
        """
        album_info: AlbumInfo | None = None

        with self._job_temp_dir(job_id) as job_temp_dir:
            try:
                # Phase 1: Enrich metadata via ytmusicapi (0% → 10%)
                self._emit_progress(
                    progress_callback,
                    ProgressStep.FETCHING_INFO,
                    "Enriching playlist metadata...",
                    PLAYLIST_PROGRESS_START,
                )

                playlist_id = extract_playlist_id(url)
                if not playlist_id:
                    return SyncResult(
                        success=False,
                        error="Could not extract playlist ID from URL",
                    )

                try:
                    enricher = MetadataEnricher()
                    playlist_meta = enricher.get_playlist(playlist_id)
                except Exception as e:
                    logger.error("Failed to enrich playlist metadata: {}", e)
                    return SyncResult(
                        success=False,
                        error=f"Failed to fetch playlist metadata: {e}",
                    )

                if not playlist_meta.tracks:
                    return SyncResult(
                        success=False,
                        error="No available tracks in playlist",
                    )

                album_info = AlbumInfo(
                    title=playlist_meta.title,
                    artist="Various Artists",
                    track_count=playlist_meta.track_count,
                    playlist_id=playlist_id,
                    url=url,
                )

                self._emit_progress(
                    progress_callback,
                    ProgressStep.FETCHING_INFO,
                    f"Found {playlist_meta.track_count} tracks: {playlist_meta.title}",
                    PLAYLIST_PROGRESS_FETCH_DONE,
                    {"album_info": album_info.model_dump()},
                )

                if cancel_check and cancel_check():
                    return SyncResult(
                        success=False,
                        album_info=album_info,
                        error="Cancelled",
                    )

                # Phase 2: Download via yt-dlp (10% → 60%)
                download_wrapper = self._create_download_progress_wrapper(
                    progress_callback,
                    playlist_meta.track_count,
                    PLAYLIST_PROGRESS_FETCH_DONE,
                    PLAYLIST_PROGRESS_DOWNLOAD_DONE,
                )

                self._emit_progress(
                    progress_callback,
                    ProgressStep.DOWNLOADING,
                    "Starting download...",
                    PLAYLIST_PROGRESS_FETCH_DONE,
                )

                download_result = self._downloader.download_album(
                    url,
                    job_temp_dir,
                    progress_callback=download_wrapper,
                    cancel_check=cancel_check,
                )

                # Check for failure/cancellation
                if download_result.cancelled:
                    return SyncResult(
                        success=False,
                        download_result=download_result,
                        album_info=album_info,
                        error="Download cancelled",
                    )

                if not download_result.success:
                    return SyncResult(
                        success=False,
                        download_result=download_result,
                        album_info=album_info,
                        error=download_result.error or "Download failed",
                    )

                downloaded_files = sorted(
                    [Path(f) for f in download_result.downloaded_files]
                )

                self._emit_progress(
                    progress_callback,
                    ProgressStep.DOWNLOADING,
                    f"Downloaded {len(downloaded_files)} tracks",
                    PLAYLIST_PROGRESS_DOWNLOAD_DONE,
                )

                # Phase 3: Patch metadata (60% → 70%)
                self._emit_progress(
                    progress_callback,
                    ProgressStep.IMPORTING,
                    "Patching track metadata...",
                    PLAYLIST_PROGRESS_DOWNLOAD_DONE,
                )

                patcher = MetadataPatcher()
                patcher.patch_files(
                    file_paths=downloaded_files,
                    track_metadata=playlist_meta.tracks,
                    playlist_name=playlist_meta.title,
                )

                self._emit_progress(
                    progress_callback,
                    ProgressStep.IMPORTING,
                    "Metadata patched",
                    PLAYLIST_PROGRESS_PATCH_DONE,
                )

                # Phase 4: Organize files to Playlists/{name}/ (70% → 75%)
                final_files = self._organize_playlist_files(
                    downloaded_files,
                    playlist_meta,
                    progress_callback,
                )

                # Phase 5: Beets import in place (75% → 90%)
                self._emit_progress(
                    progress_callback,
                    ProgressStep.IMPORTING,
                    "Running beets enrichment...",
                    PLAYLIST_PROGRESS_ORGANIZE_DONE,
                )

                tag_result = self._tagger.tag_playlist(
                    final_files, progress_callback=progress_callback
                )

                if not tag_result.success:
                    logger.warning(
                        "Beets enrichment failed (non-fatal): {}", tag_result.error
                    )

                self._emit_progress(
                    progress_callback,
                    ProgressStep.IMPORTING,
                    "Beets enrichment complete",
                    PLAYLIST_PROGRESS_BEETS_DONE,
                )

                # Phase 6: Generate M3U (90% → 100%)
                playlist_dir = final_files[0].parent
                self._emit_progress(
                    progress_callback,
                    ProgressStep.IMPORTING,
                    "Generating playlist file...",
                    PLAYLIST_PROGRESS_BEETS_DONE,
                )

                generate_m3u(
                    playlist_name=playlist_meta.title,
                    track_files=final_files,
                    track_metadata=playlist_meta.tracks,
                    output_dir=playlist_dir,
                )

                self._emit_progress(
                    progress_callback,
                    ProgressStep.COMPLETED,
                    f"Sync complete: {playlist_dir}",
                    PLAYLIST_PROGRESS_COMPLETE,
                )

                return SyncResult(
                    success=True,
                    download_result=download_result,
                    tag_result=tag_result,
                    album_info=album_info,
                    destination=str(playlist_dir),
                )

            except Exception as e:
                logger.exception("Playlist sync failed")
                self._emit_progress(progress_callback, ProgressStep.FAILED, str(e))
                return SyncResult(
                    success=False,
                    album_info=album_info,
                    error=str(e),
                )

    def _organize_playlist_files(
        self,
        downloaded_files: list[Path],
        playlist_meta: PlaylistMetadata,
        progress_callback: ProgressCallback | None,
    ) -> list[Path]:
        """Organize downloaded files into playlist directory with proper naming."""
        self._emit_progress(
            progress_callback,
            ProgressStep.IMPORTING,
            "Organizing files...",
            PLAYLIST_PROGRESS_PATCH_DONE,
        )

        playlist_dir = self.playlists_dir / sanitize_filename(playlist_meta.title)
        playlist_dir.mkdir(parents=True, exist_ok=True)

        if len(downloaded_files) != len(playlist_meta.tracks):
            logger.warning(
                "Downloaded {} files but expected {} from metadata. "
                "Processing available files.",
                len(downloaded_files),
                len(playlist_meta.tracks),
            )

        final_files: list[Path] = []
        for downloaded_file, track in zip(
            downloaded_files, playlist_meta.tracks, strict=False
        ):
            safe_artist = sanitize_filename(track.artist)
            safe_title = sanitize_filename(track.title)
            new_name = (
                f"{track.track_number:02d} - {safe_artist} - "
                f"{safe_title}{downloaded_file.suffix}"
            )
            dest = playlist_dir / new_name

            if dest.exists():
                logger.info("Overwriting existing file: {}", dest)
                dest.unlink()

            shutil.move(str(downloaded_file), str(dest))
            final_files.append(dest)

        self._emit_progress(
            progress_callback,
            ProgressStep.IMPORTING,
            f"Files organized to {playlist_dir.name}/",
            PLAYLIST_PROGRESS_ORGANIZE_DONE,
        )

        return final_files
