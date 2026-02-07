"""High-level playlist download pipeline."""

import logging
from collections.abc import Iterator
from pathlib import Path

from yubal.client import YTMusicClient, YTMusicProtocol
from yubal.config import PlaylistDownloadConfig
from yubal.exceptions import CancellationError
from yubal.models.cancel import CancelToken
from yubal.models.enums import ContentKind, DownloadStatus, SkipReason
from yubal.models.progress import ExtractProgress, PlaylistProgress
from yubal.models.results import (
    DownloadResult,
    PlaylistDownloadResult,
    aggregate_skip_reasons,
)
from yubal.models.track import PlaylistInfo, TrackMetadata, UnavailableTrack
from yubal.services.artifacts import (
    ArtifactPaths,
    PlaylistArtifactsProtocol,
    PlaylistArtifactsService,
)
from yubal.services.downloader import DownloadService
from yubal.services.extractor import MetadataExtractorService
from yubal.services.replaygain import ReplayGainProtocol, ReplayGainService

logger = logging.getLogger(__name__)


def _format_skip_summary(
    unavailable: list[UnavailableTrack],
    skipped_by_reason: dict[SkipReason, int],
) -> str:
    """Format skip reasons into human-readable summary.

    Args:
        unavailable: Tracks YouTube reports as unavailable at source.
        skipped_by_reason: Tracks skipped during extraction (e.g., unsupported type).

    Returns:
        Formatted string like "3 unavailable, 2 unsupported video type".
    """
    parts: list[str] = []
    if unavailable:
        parts.append(f"{len(unavailable)} unavailable")
    for reason, count in skipped_by_reason.items():
        parts.append(f"{count} {reason.label}")
    return ", ".join(parts)


class PlaylistDownloadService:
    """High-level orchestration service for complete playlist downloads.

    Pipeline Overview:
    ==================
    1. download_playlist() - Main entry point: orchestrates four-phase pipeline
                   and yields progress updates after each track/milestone
    2. _execute_extraction_phase() - Phase 1: Extracts all track metadata from
                   YouTube Music playlist, yielding progress after each track
    3. _execute_download_phase() - Phase 2: Downloads all tracks to disk using
                   yt-dlp, yielding progress after each download completion
    4. _execute_composition_phase() - Phase 3: Generates M3U playlist files and
                   saves cover art to filesystem
    5. _execute_normalization_phase() - Phase 4: Applies ReplayGain tags using
                   rsgain (optional, only if apply_replaygain is enabled)
    6. _build_final_result() - Constructs the final result object with all
                   download outcomes and artifact paths

    This service provides the recommended high-level interface for playlist
    downloads. It handles the complete workflow: extraction, downloading, and
    artifact generation. Use this when you want a complete, production-ready
    playlist download experience.

    For lower-level control, use the individual services directly
    (MetadataExtractorService, DownloadService, PlaylistArtifactsService).

    Example:
        >>> from yubal import create_playlist_downloader
        >>> from yubal.config import PlaylistDownloadConfig, DownloadConfig
        >>>
        >>> config = PlaylistDownloadConfig(
        ...     download=DownloadConfig(base_path=Path("./music"))
        ... )
        >>> service = create_playlist_downloader(config)
        >>>
        >>> # With progress updates
        >>> for progress in service.download_playlist(url):
        ...     print(f"[{progress.phase}] {progress.current}/{progress.total}")
        >>> result = service.get_result()
        >>> print(f"Downloaded: {result.success_count}")
        >>>
        >>> # Or all at once
        >>> result = service.download_playlist_all(url)
    """

    def __init__(
        self,
        config: PlaylistDownloadConfig,
        *,
        client: YTMusicProtocol | None = None,
        extractor: MetadataExtractorService | None = None,
        downloader: DownloadService | None = None,
        composer: PlaylistArtifactsProtocol | None = None,
        replaygain: ReplayGainProtocol | None = None,
        cookies_path: Path | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            config: Playlist download configuration.
            client: Optional YTMusic client (creates default if not provided).
            extractor: Optional extractor (creates from client if not provided).
            downloader: Optional downloader (creates from config if not provided).
            composer: Optional composer (creates default if not provided).
            replaygain: Optional ReplayGain service (creates default if not provided).
            cookies_path: Optional path to cookies.txt for authentication.
        """
        self._config = config

        # Create client if needed
        if client is None:
            client = YTMusicClient(cookies_path=cookies_path)

        # Create services
        self._extractor = extractor or MetadataExtractorService(client)
        self._downloader = downloader or DownloadService(
            config.download, cookies_path=cookies_path
        )
        self._composer = composer or PlaylistArtifactsService()
        self._replaygain = replaygain or ReplayGainService()

        # Store last result for retrieval after iteration
        self._last_result: PlaylistDownloadResult | None = None

    # ============================================================================
    # PUBLIC API - Main entry points for playlist downloads
    # ============================================================================

    def download_playlist(
        self,
        url: str,
        cancel_token: CancelToken | None = None,
    ) -> Iterator[PlaylistProgress]:
        """Execute complete playlist download pipeline with progress updates.

        This is the main orchestration method that runs all four phases
        sequentially while yielding progress updates. Each phase checks for
        cancellation before starting, allowing graceful cancellation between
        phases rather than mid-operation.

        Why yield progress: Long-running downloads (hundreds of tracks) need
        real-time feedback for CLI progress bars, web UI updates, or logging.
        Progress updates are yielded after each track extraction/download and
        at composition milestones.

        Pipeline phases:
        1. "extracting" - Fetch track metadata from YouTube Music API
        2. "downloading" - Download audio files via yt-dlp (respects skip logic)
        3. "composing" - Generate M3U playlist files and save cover art
        4. "normalizing" - Apply ReplayGain tags (optional, if enabled)

        Args:
            url: YouTube Music playlist URL.
            cancel_token: Optional token for cancellation support. Checked
                before each phase starts (not during individual operations).

        Yields:
            PlaylistProgress with phase indicator, counts, and phase-specific
            data (extract_progress or download_progress).

        Raises:
            CancellationError: If cancel_token.is_cancelled becomes True.
            PlaylistParseError: If URL is invalid.
            PlaylistNotFoundError: If playlist doesn't exist.
            APIError: If API requests fail.

        Example:
            >>> for progress in service.download_playlist(url):
            ...     if progress.phase == "extracting":
            ...         print(f"Extracting: {progress.current}/{progress.total}")
            ...     elif progress.phase == "downloading":
            ...         result = progress.download_progress.result
            ...         print(f"Downloaded: {result.track.title}")
        """
        # Check for cancellation before starting
        self._check_cancellation(cancel_token)

        # Log pipeline start
        logger.info(
            "Starting new download",
            extra={"header": "New Download"},
        )
        logger.info("URL: %s", url)

        # Phase 1: Extract metadata (handles all URL types: track, album, playlist)
        extracted_tracks: list[TrackMetadata] = []
        playlist_info: PlaylistInfo | None = None

        for progress, extract_progress in self._extract_phase(url, cancel_token):
            if extract_progress.track is not None:
                extracted_tracks.append(extract_progress.track)
            playlist_info = extract_progress.playlist_info
            yield progress

        # Early exit if no tracks found
        if not extracted_tracks or not playlist_info:
            logger.warning("No tracks extracted, nothing to download")
            self._last_result = None
            return

        # Phase 2: Download tracks to disk
        download_results: list[DownloadResult] = []

        for progress, result in self._download_phase(extracted_tracks, cancel_token):
            download_results.append(result)
            yield progress

        # Log download statistics
        self._log_download_stats(download_results)

        # Phase 3: Generate playlist artifacts
        artifacts = ArtifactPaths()

        for progress, phase_artifacts in self._compose_phase(
            playlist_info, download_results, cancel_token
        ):
            artifacts = phase_artifacts
            yield progress

        # Phase 4: Apply ReplayGain tags (optional)
        if self._config.apply_replaygain:
            yield from self._normalize_phase(
                playlist_info,
                download_results,
                expected_count=len(extracted_tracks),
                cancel_token=cancel_token,
            )

        # Store complete result for retrieval via get_result()
        self._last_result = self._build_final_result(
            playlist_info, download_results, artifacts
        )

        kind = playlist_info.kind.value.capitalize()
        logger.info("%s download complete", kind, extra={"status": "success"})

    def download_playlist_all(
        self,
        url: str,
        cancel_token: CancelToken | None = None,
    ) -> PlaylistDownloadResult:
        """Execute complete playlist download and return final result.

        Convenience wrapper around download_playlist() that consumes all progress
        updates silently and returns only the final result. Use this when you
        don't need incremental progress updates (e.g., in tests, scripts, or
        simple CLI tools without progress bars).

        Why use this: Simpler API for cases where you just want the result
        without handling progress updates. Equivalent to consuming the
        download_playlist() iterator and calling get_result().

        Args:
            url: YouTube Music playlist URL.
            cancel_token: Optional token for cancellation support.

        Returns:
            Complete playlist download result with all download outcomes
            and generated artifact paths.

        Raises:
            ValueError: If the download yields no result (empty playlist).
            CancellationError: If cancel_token.is_cancelled becomes True.
            PlaylistParseError: If URL is invalid.
            PlaylistNotFoundError: If playlist doesn't exist.
            APIError: If API requests fail.

        Example:
            >>> result = service.download_playlist_all(url)
            >>> print(f"Downloaded {result.success_count} tracks")
            >>> print(f"M3U saved to: {result.m3u_path}")
        """
        # Consume iterator
        for _ in self.download_playlist(url, cancel_token):
            pass

        if self._last_result is None:
            raise ValueError("No tracks found in playlist")

        return self._last_result

    def get_result(self) -> PlaylistDownloadResult | None:
        """Retrieve the result of the most recent download operation.

        Why this exists: Allows callers to retrieve the final result after
        consuming the download_playlist() iterator. This is the recommended
        pattern for progress-driven downloads:
        1. Iterate through download_playlist() for progress updates
        2. Call get_result() to get the complete result object

        Returns:
            The last download result with all outcomes and artifact paths,
            or None if no download has completed yet.
        """
        return self._last_result

    # ============================================================================
    # CANCELLATION SUPPORT - Check and handle cancellation requests
    # ============================================================================

    def _check_cancellation(self, cancel_token: CancelToken | None) -> None:
        """Check if operation has been cancelled and raise exception if so.

        Args:
            cancel_token: Optional cancellation token to check.

        Raises:
            CancellationError: If cancel_token.is_cancelled is True.
        """
        if cancel_token and cancel_token.is_cancelled:
            raise CancellationError("Operation cancelled")

    # ============================================================================
    # PHASE 1: EXTRACTION - Fetch track metadata from YouTube Music
    # ============================================================================

    def _extract_phase(
        self,
        url: str,
        cancel_token: CancelToken | None,
    ) -> Iterator[tuple[PlaylistProgress, ExtractProgress]]:
        """Execute metadata extraction phase with progress updates.

        Fetches track metadata from the YouTube Music URL. Handles all URL types
        (single track, album, playlist). Yields (progress, extract_progress)
        tuples so the caller can collect tracks and playlist info.

        Args:
            url: YouTube Music URL (single track, album, or playlist).
            cancel_token: Optional cancellation token.

        Yields:
            Tuples of (PlaylistProgress, ExtractProgress). The caller collects
            tracks from extract_progress.track and playlist_info.
        """
        logger.info(
            "Fetching metadata",
            extra={"phase": "extracting", "phase_num": 1},
        )

        extracted_count = 0
        last_progress = None

        for progress in self._extractor.extract(url, max_items=self._config.max_items):
            if progress.track is not None:
                extracted_count += 1
            last_progress = progress
            yield (
                PlaylistProgress(
                    phase="extracting",
                    current=progress.current,
                    total=progress.total,
                    extract_progress=progress,
                ),
                progress,
            )

        # Log extraction summary
        if last_progress:
            unavailable = last_progress.playlist_info.unavailable_tracks
            extraction_skipped = last_progress.skipped_by_reason
            total_skipped = len(unavailable) + sum(extraction_skipped.values())
            total_in_playlist = extracted_count + total_skipped
            kind = last_progress.playlist_info.kind.value.capitalize()

            if total_skipped:
                skip_summary = _format_skip_summary(unavailable, extraction_skipped)
                logger.info(
                    "%s contains %d tracks (%d skipped: %s)",
                    kind,
                    total_in_playlist,
                    total_skipped,
                    skip_summary,
                )
                for ut in unavailable:
                    logger.info(
                        "  - %s by %s (%s)",
                        ut.title or "Unknown",
                        ut.artist_display,
                        ut.reason.label,
                    )
            else:
                logger.info("%s contains %d tracks", kind, total_in_playlist)

    # ============================================================================
    # PHASE 2: DOWNLOAD - Download tracks to disk via yt-dlp
    # ============================================================================

    def _download_phase(
        self,
        tracks: list[TrackMetadata],
        cancel_token: CancelToken | None,
    ) -> Iterator[tuple[PlaylistProgress, DownloadResult]]:
        """Execute track download phase with progress updates.

        Downloads all tracks to disk using yt-dlp. Yields (progress, result)
        tuples so the caller can collect download results.

        Args:
            tracks: List of track metadata to download.
            cancel_token: Optional cancellation token (checked by DownloadService).

        Yields:
            Tuples of (PlaylistProgress, DownloadResult). The caller collects
            results into a local list.
        """
        self._check_cancellation(cancel_token)

        logger.info(
            "Downloading %d tracks",
            len(tracks),
            extra={"phase": "downloading", "phase_num": 2},
        )

        for progress in self._downloader.download_tracks(tracks, cancel_token):
            yield (
                PlaylistProgress(
                    phase="downloading",
                    current=progress.current,
                    total=progress.total,
                    download_progress=progress,
                ),
                progress.result,
            )

    def _log_download_stats(self, results: list[DownloadResult]) -> None:
        """Log download statistics after download phase completes."""
        success_count = sum(1 for r in results if r.status == DownloadStatus.SUCCESS)
        failed_count = sum(1 for r in results if r.status == DownloadStatus.FAILED)
        skipped_by_reason = aggregate_skip_reasons(results)

        logger.info(
            "Downloads complete",
            extra={
                "stats": {
                    "stats_type": "download",
                    "success": success_count,
                    "failed": failed_count,
                    "skipped_by_reason": {
                        k.value: v for k, v in skipped_by_reason.items()
                    },
                }
            },
        )

    # ============================================================================
    # PHASE 3: COMPOSITION - Generate M3U playlists and save cover art
    # ============================================================================

    def _compose_phase(
        self,
        playlist_info: PlaylistInfo,
        results: list[DownloadResult],
        cancel_token: CancelToken | None,
    ) -> Iterator[tuple[PlaylistProgress, ArtifactPaths]]:
        """Execute playlist composition phase with progress updates.

        Generates M3U playlist files and saves cover art to disk. Yields
        (progress, ArtifactPaths) tuples so the caller can collect
        the artifact paths.

        Args:
            playlist_info: Playlist metadata for file generation.
            results: Download results to include in M3U files.
            cancel_token: Optional cancellation token.

        Yields:
            Tuples of (PlaylistProgress, ArtifactPaths).
        """
        self._check_cancellation(cancel_token)

        # Determine what we're actually generating
        is_album = playlist_info.kind == ContentKind.ALBUM
        is_track = playlist_info.kind == ContentKind.TRACK
        will_generate_m3u = self._config.generate_m3u and not (
            is_track or (self._config.skip_album_m3u and is_album)
        )
        will_save_cover = self._config.save_cover and not is_track

        # Build phase message based on what we're doing
        if will_generate_m3u or will_save_cover:
            actions = []
            if will_generate_m3u:
                actions.append("playlist file")
            if will_save_cover:
                actions.append("cover")
            message = f"Saving {' and '.join(actions)}"
        elif is_track:
            message = "Single track, no artifacts"
        else:
            message = "No artifacts to generate"

        logger.info(message, extra={"phase": "composing", "phase_num": 3})

        yield (
            PlaylistProgress(
                phase="composing",
                current=0,
                total=1,
                message=message,
            ),
            ArtifactPaths(),
        )

        artifact_paths = self._composer.compose(
            self._config.download.base_path,
            playlist_info,
            results,
            generate_m3u=self._config.generate_m3u,
            save_cover=self._config.save_cover,
            skip_album_m3u=self._config.skip_album_m3u,
        )

        yield (
            PlaylistProgress(
                phase="composing",
                current=1,
                total=1,
                message="Done",
            ),
            artifact_paths,
        )

    # ============================================================================
    # PHASE 4: NORMALIZATION - Apply ReplayGain tags using rsgain
    # ============================================================================

    def _normalize_phase(
        self,
        playlist_info: PlaylistInfo,
        results: list[DownloadResult],
        *,
        expected_count: int,
        cancel_token: CancelToken | None,
    ) -> Iterator[PlaylistProgress]:
        """Execute ReplayGain normalization phase with progress updates.

        Applies ReplayGain/R128 tags to successfully downloaded tracks using
        rsgain. For complete album downloads, calculates both album and track
        gain. For partial downloads or playlists, only calculates track gain.

        This phase is optional and only runs if apply_replaygain is enabled.
        All errors are non-fatal - the pipeline continues even if rsgain fails.

        Args:
            playlist_info: Playlist metadata for determining album mode.
            results: Download results to identify successful downloads.
            expected_count: Number of tracks expected (for album completeness check).
            cancel_token: Optional cancellation token.

        Yields:
            PlaylistProgress with phase="normalizing" and status messages.
        """
        self._check_cancellation(cancel_token)

        # Collect successfully downloaded files
        downloaded_files = [
            r.output_path
            for r in results
            if r.status == DownloadStatus.SUCCESS and r.output_path
        ]

        if not downloaded_files:
            logger.debug("No files to normalize")
            return

        # Determine if this is a complete album (use album mode)
        success_count = sum(1 for r in results if r.status == DownloadStatus.SUCCESS)
        is_complete_album = (
            playlist_info.kind == ContentKind.ALBUM
            and self._config.max_items is None
            and success_count == expected_count
        )

        mode_desc = "album + track gain" if is_complete_album else "track gain only"
        logger.info(
            "Applying ReplayGain (%s) to %d file(s)",
            mode_desc,
            len(downloaded_files),
            extra={"phase": "normalizing", "phase_num": 4},
        )

        yield PlaylistProgress(
            phase="normalizing",
            current=0,
            total=1,
            message=f"Applying ReplayGain ({mode_desc})...",
        )

        success = self._replaygain.apply_replaygain(
            downloaded_files,
            self._config.download.codec,
            album_mode=is_complete_album,
        )

        if success:
            yield PlaylistProgress(
                phase="normalizing",
                current=1,
                total=1,
                message="ReplayGain applied",
            )
        else:
            # Non-fatal: warn but continue
            yield PlaylistProgress(
                phase="normalizing",
                current=1,
                total=1,
                message="ReplayGain skipped (rsgain unavailable or failed)",
            )

    # ============================================================================
    # RESULT CONSTRUCTION - Build final result object
    # ============================================================================

    def _build_final_result(
        self,
        playlist_info: PlaylistInfo,
        results: list[DownloadResult],
        artifacts: ArtifactPaths,
    ) -> PlaylistDownloadResult:
        """Construct final result object with all download outcomes.

        Args:
            playlist_info: Metadata about the playlist.
            results: All download results from phase 2.
            artifacts: Paths to generated playlist artifacts.

        Returns:
            Complete playlist download result.
        """
        return PlaylistDownloadResult(
            playlist_info=playlist_info,
            download_results=results,
            m3u_path=artifacts.m3u,
            cover_path=artifacts.cover,
        )
