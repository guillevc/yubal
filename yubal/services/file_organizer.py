"""File organization service for playlist downloads."""

import shutil
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from yubal.services.m3u_generator import sanitize_filename
from yubal.services.metadata_enricher import PlaylistMetadata, TrackMetadata


@dataclass
class FileOrganizer:
    """Service for organizing downloaded files into playlist directories.

    Handles moving downloaded files to their final destination with proper
    naming conventions based on track metadata.

    Attributes:
        playlists_dir: Base directory for playlist outputs (e.g., ~/Music/Playlists)
    """

    playlists_dir: Path

    def organize(
        self,
        downloaded_files: list[Path],
        playlist_meta: PlaylistMetadata,
    ) -> list[Path]:
        """Organize downloaded files into playlist directory with proper naming.

        Moves files to Playlists/{sanitized_name}/ with format:
        "{track_number:02d} - {artist} - {title}.{ext}"

        Args:
            downloaded_files: List of downloaded audio file paths (sorted)
            playlist_meta: Playlist metadata containing track info

        Returns:
            List of final file paths in the organized directory
        """
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
            dest = self._get_destination_path(downloaded_file, track, playlist_dir)

            if dest.exists():
                logger.info("Overwriting existing file: {}", dest)
                dest.unlink()

            shutil.move(str(downloaded_file), str(dest))
            final_files.append(dest)

        return final_files

    def _get_destination_path(
        self,
        source_file: Path,
        track: TrackMetadata,
        playlist_dir: Path,
    ) -> Path:
        """Generate the destination path for a track file.

        Args:
            source_file: Original downloaded file
            track: Track metadata for naming
            playlist_dir: Target directory

        Returns:
            Full path for the organized file
        """
        safe_artist = sanitize_filename(track.artist)
        safe_title = sanitize_filename(track.title)
        new_name = (
            f"{track.track_number:02d} - {safe_artist} - "
            f"{safe_title}{source_file.suffix}"
        )
        return playlist_dir / new_name
