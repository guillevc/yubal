"""Playlist artifacts service for generating M3U and cover files."""

import logging
from pathlib import Path
from typing import NamedTuple, Protocol

from yubal.models.enums import ContentKind, DownloadStatus
from yubal.models.results import DownloadResult
from yubal.models.track import PlaylistInfo, TrackMetadata
from yubal.utils.m3u import write_m3u, write_playlist_cover

logger = logging.getLogger(__name__)


class ArtifactPaths(NamedTuple):
    """Paths to generated playlist artifacts.

    NamedTuple so callers can destructure: ``m3u, cover = composer.compose(...)``
    """

    m3u: Path | None = None
    cover: Path | None = None


class PlaylistArtifactsProtocol(Protocol):
    """Protocol for playlist artifact generation services.

    Enables dependency injection and testing of artifact generation.
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
    ) -> ArtifactPaths:
        """Generate playlist artifacts (M3U file and cover image)."""
        ...


class PlaylistArtifactsService:
    """Service for generating playlist artifacts (M3U files and covers).

    Pipeline Overview:
    ==================
    1. compose() - Main entry point: orchestrates M3U and cover generation
                   based on configuration flags and content type
    2. _collect_successful_tracks_for_playlist() - Filters download results
                   to include only successful and skipped tracks (both should
                   appear in the final playlist)
    3. Delegates to utility functions (write_m3u, write_playlist_cover) for
       actual file generation

    This service is stateless and operates purely on the results of completed
    downloads. It does not perform any downloads or API calls itself.

    Example:
        >>> composer = PlaylistArtifactsService()
        >>> artifacts = composer.compose(
        ...     base_path=Path("./music"),
        ...     playlist_info=playlist_info,
        ...     results=download_results,
        ... )
        >>> artifacts.m3u   # Path or None
        >>> artifacts.cover  # Path or None
    """

    # ============================================================================
    # PUBLIC API - Main entry point for playlist artifact generation
    # ============================================================================

    def compose(
        self,
        base_path: Path,
        playlist_info: PlaylistInfo,
        results: list[DownloadResult],
        *,
        generate_m3u: bool = True,
        save_cover: bool = True,
        skip_album_m3u: bool = True,
    ) -> ArtifactPaths:
        """Generate playlist artifacts (M3U file and cover image) from downloads.

        This is the main composition pipeline. It takes completed download results
        and generates two types of artifacts:
        1. M3U playlist file - Contains relative paths to all tracks
        2. Playlist cover image - Saved as a sidecar JPEG file

        Why skip album M3U: Albums already have an inherent folder structure
        (one folder per album with all tracks inside). An M3U file is redundant
        for albums but valuable for curated playlists where tracks come from
        different albums and folders.

        Why include skipped tracks: Both SUCCESS and SKIPPED tracks should appear
        in the playlist. SKIPPED means the file already existed and was not
        re-downloaded, but it's still part of the playlist.

        Args:
            base_path: Base directory for output files.
            playlist_info: Playlist metadata (title, cover URL, content type).
            results: Download results with output paths and status.
            generate_m3u: Whether to generate M3U playlist file.
            save_cover: Whether to save playlist cover image.
            skip_album_m3u: Skip M3U generation for album playlists
                (they already have their own folder structure).

        Returns:
            ArtifactPaths with m3u and cover paths. Either may be None if
            not generated, not configured, or if generation failed.
        """
        m3u_path: Path | None = None
        cover_path: Path | None = None

        playlist_name = playlist_info.title or "Untitled Playlist"

        # Generate M3U playlist
        if generate_m3u:
            m3u_path = self._generate_m3u_if_needed(
                base_path=base_path,
                playlist_name=playlist_name,
                playlist_info=playlist_info,
                results=results,
                skip_album_m3u=skip_album_m3u,
            )

        # Save playlist cover
        if save_cover:
            cover_path = self._save_cover_if_available(
                base_path=base_path,
                playlist_name=playlist_name,
                playlist_info=playlist_info,
            )

        return ArtifactPaths(m3u=m3u_path, cover=cover_path)

    # ============================================================================
    # M3U GENERATION - Create playlist file with track paths
    # ============================================================================

    def _generate_m3u_if_needed(
        self,
        base_path: Path,
        playlist_name: str,
        playlist_info: PlaylistInfo,
        results: list[DownloadResult],
        skip_album_m3u: bool,
    ) -> Path | None:
        """Generate M3U playlist file if appropriate for this content type.

        Why skip albums: Albums have an inherent folder structure with all tracks
        in a single directory. An M3U file is redundant for albums but valuable
        for curated playlists where tracks span multiple albums/folders.

        Args:
            base_path: Base directory for output files.
            playlist_name: Name to use for the M3U file.
            playlist_info: Playlist metadata (content type, etc.).
            results: Download results to include in M3U.
            skip_album_m3u: Whether to skip M3U generation for albums.

        Returns:
            Path to generated M3U file, or None if skipped/failed/no tracks.
        """
        # Skip albums if configured (they have inherent folder structure)
        if skip_album_m3u and playlist_info.kind == ContentKind.ALBUM:
            logger.debug("Skipping M3U for album: %s", playlist_info.playlist_id)
            return None

        # Skip single tracks (M3U is for playlists, not individual tracks)
        if playlist_info.kind == ContentKind.TRACK:
            logger.debug("Skipping M3U for single track: %s", playlist_info.playlist_id)
            return None

        tracks = self._collect_successful_tracks_for_playlist(results)
        if not tracks:
            logger.debug("No tracks available for M3U generation")
            return None

        m3u_path = write_m3u(
            base_path, playlist_name, playlist_info.playlist_id, tracks
        )
        logger.info(
            "Generated M3U playlist: '%s'",
            m3u_path,
            extra={"file_type": "m3u", "file_path": str(m3u_path)},
        )
        return m3u_path

    def _collect_successful_tracks_for_playlist(
        self, results: list[DownloadResult]
    ) -> list[tuple[TrackMetadata, Path]]:
        """Collect successful and skipped tracks for playlist inclusion.

        Why include both SUCCESS and SKIPPED: Both represent tracks that exist
        on disk and should appear in the final playlist. SUCCESS means we just
        downloaded it, SKIPPED means it already existed. Either way, it's part
        of the playlist.

        Why exclude FAILED: Failed downloads don't have output files, so they
        can't be included in the M3U playlist (no path to reference).

        Args:
            results: Download results to filter.

        Returns:
            List of (track_metadata, output_path) tuples for M3U generation.
            Only includes tracks with SUCCESS or SKIPPED status.
        """
        return [
            (result.track, result.output_path)
            for result in results
            if result.status in (DownloadStatus.SUCCESS, DownloadStatus.SKIPPED)
            and result.output_path
        ]

    # ============================================================================
    # COVER GENERATION - Save playlist cover image
    # ============================================================================

    def _save_cover_if_available(
        self,
        base_path: Path,
        playlist_name: str,
        playlist_info: PlaylistInfo,
    ) -> Path | None:
        """Save playlist cover image as a sidecar JPEG file.

        Why sidecar files: Storing the cover as a separate file (e.g.,
        "playlist.jpg") allows music players and file browsers to display
        playlist artwork without parsing audio files.

        Args:
            base_path: Base directory for output files.
            playlist_name: Name to use for the cover file.
            playlist_info: Playlist metadata (cover URL, etc.).

        Returns:
            Path to saved cover file, or None if no cover URL or save failed.
        """
        if not playlist_info.cover_url:
            return None

        # Skip single tracks (cover saved with the track file, not separately)
        if playlist_info.kind == ContentKind.TRACK:
            logger.debug(
                "Skipping playlist cover for single track: %s",
                playlist_info.playlist_id,
            )
            return None

        cover_path = write_playlist_cover(
            base_path, playlist_name, playlist_info.playlist_id, playlist_info.cover_url
        )
        if cover_path:
            logger.info(
                "Saved cover: '%s'",
                cover_path,
                extra={"file_type": "cover", "file_path": str(cover_path)},
            )
        return cover_path
