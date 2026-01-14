"""Playlist composition service for generating M3U and cover files."""

import logging
from pathlib import Path

from yubal.models.domain import (
    DownloadResult,
    DownloadStatus,
    PlaylistInfo,
    TrackMetadata,
)
from yubal.utils.m3u import write_m3u, write_playlist_cover
from yubal.utils.playlist import is_album_playlist

logger = logging.getLogger(__name__)


class PlaylistComposerService:
    """Service for generating playlist artifacts (M3U files and covers).

    Takes completed download results and generates:
    - M3U playlist file with relative paths to tracks
    - Playlist cover image as a sidecar JPEG file

    This service is stateless and can be used independently of the
    download workflow.

    Example:
        >>> composer = PlaylistComposerService()
        >>> m3u_path, cover_path = composer.compose(
        ...     base_path=Path("./music"),
        ...     playlist_info=playlist_info,
        ...     results=download_results,
        ... )
    """

    def compose(
        self,
        base_path: Path,
        playlist_info: PlaylistInfo,
        results: list[DownloadResult],
        *,
        generate_m3u: bool = True,
        save_cover: bool = True,
        skip_album_m3u: bool = True,
    ) -> tuple[Path | None, Path | None]:
        """Generate playlist artifacts from download results.

        Args:
            base_path: Base directory for output files.
            playlist_info: Playlist metadata (title, cover URL, etc.).
            results: Download results with output paths.
            generate_m3u: Whether to generate M3U playlist file.
            save_cover: Whether to save playlist cover image.
            skip_album_m3u: Skip M3U generation for album playlists
                (they already have their own folder structure).

        Returns:
            Tuple of (m3u_path, cover_path). Either may be None if
            not generated or if generation failed.
        """
        m3u_path: Path | None = None
        cover_path: Path | None = None

        playlist_name = playlist_info.title or "Untitled Playlist"

        # Generate M3U playlist
        if generate_m3u:
            # Skip album playlists if configured (they have inherent structure)
            if skip_album_m3u and is_album_playlist(playlist_info.playlist_id):
                logger.debug(
                    "Skipping M3U for album playlist: %s", playlist_info.playlist_id
                )
            else:
                tracks = self._collect_tracks_for_m3u(results)
                if tracks:
                    m3u_path = write_m3u(base_path, playlist_name, tracks)
                    logger.info("Generated M3U playlist: %s", m3u_path)
                else:
                    logger.debug("No tracks available for M3U generation")

        # Save playlist cover
        if save_cover and playlist_info.cover_url:
            cover_path = write_playlist_cover(
                base_path, playlist_name, playlist_info.cover_url
            )
            if cover_path:
                logger.info("Saved playlist cover: %s", cover_path)

        return m3u_path, cover_path

    def _collect_tracks_for_m3u(
        self, results: list[DownloadResult]
    ) -> list[tuple[TrackMetadata, Path]]:
        """Collect successful downloads for M3U generation.

        Includes both newly downloaded and skipped (already existing) tracks,
        as both should appear in the playlist.

        Args:
            results: Download results to filter.

        Returns:
            List of (track_metadata, output_path) tuples for M3U generation.
        """
        tracks: list[tuple[TrackMetadata, Path]] = []
        for result in results:
            if result.status in (DownloadStatus.SUCCESS, DownloadStatus.SKIPPED):
                if result.output_path:
                    tracks.append((result.track, result.output_path))
        return tracks
