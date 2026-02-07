"""Audio file tagging service using mediafile."""

import logging
from pathlib import Path

from mediafile import Image, MediaFile

from yubal.models.track import TrackMetadata

logger = logging.getLogger(__name__)


class AudioFileTaggingService:
    """Service for applying metadata tags to audio files.

    Pipeline Overview:
    ==================
    1. apply_metadata_tags() - Main entry point: writes all metadata to audio file
    2. _write_basic_metadata() - Applies core tags (title, artist, album)
    3. _write_track_numbering() - Applies track position information
    4. _write_year_metadata() - Parses and applies release year
    5. _write_cover_art() - Embeds album artwork into the file

    Why use mediafile: The mediafile library provides a unified interface for
    tagging multiple audio formats (MP3, FLAC, M4A, etc.) with proper format-specific
    handling (ID3 tags for MP3, Vorbis comments for FLAC, etc.).
    """

    # ============================================================================
    # PUBLIC API - Main entry point for tagging audio files
    # ============================================================================

    def apply_metadata_tags(
        self, path: Path, track: TrackMetadata, cover: bytes | None = None
    ) -> None:
        """Apply complete metadata tags to an audio file.

        This is the main tagging pipeline. It writes all available metadata to the
        audio file in the correct format for that file type. The mediafile library
        handles format-specific details (ID3v2 for MP3, Vorbis for FLAC, etc.).

        Why separate steps: Breaking tagging into logical sections (basic metadata,
        track numbers, year, cover art) makes it easier to debug issues and add
        format-specific handling in the future.

        What gets written:
        - Basic metadata: title, artist(s), album, album artist(s)
        - Track numbering: track position and total tracks
        - Release year: parsed from string to integer
        - Cover art: JPEG or PNG embedded image

        Args:
            path: Path to the audio file to tag.
            track: Complete track metadata to write.
            cover: Optional cover art bytes (JPEG or PNG). The Image class
                auto-detects MIME type from magic bytes.

        Raises:
            Exception: If tagging fails. Caller should handle gracefully to avoid
                stopping the entire download process due to one tagging error.

        Example:
            >>> tagger = AudioFileTaggingService()
            >>> tagger.apply_metadata_tags(
            ...     Path("track.mp3"),
            ...     track_metadata,
            ...     cover_bytes
            ... )
        """
        audio = MediaFile(path)

        self._write_basic_metadata(audio, track)
        self._write_track_numbering(audio, track)
        self._write_year_metadata(audio, track)
        self._write_cover_art(audio, cover)

        audio.save()
        logger.debug("Successfully tagged: %s", path)

    # ============================================================================
    # METADATA WRITING - Individual steps for writing different tag categories
    # ============================================================================

    def _write_basic_metadata(self, audio: MediaFile, track: TrackMetadata) -> None:
        """Write core metadata fields to audio file.

        Why these fields: Title, artist, album, and album artist are the fundamental
        metadata fields that all music players display. These fields should always
        be present.

        Multi-artist strategy for Jellyfin + Navidrome:
        - ARTIST (singular): Delimiter-joined string for display and Jellyfin parsing
        - ARTISTS (plural): Multi-value tag preferred by Navidrome

        Args:
            audio: MediaFile instance to modify.
            track: Metadata containing basic tag information.
        """
        audio.title = track.title
        audio.album = track.album

        # Delimiter-joined for display and Jellyfin parsing
        audio.artist = track.artist  # Joined with " / "
        audio.albumartist = track.album_artist  # Joined with " / "

        # Multi-value for Navidrome (and Jellyfin with PreferNonstandardArtistsTag)
        audio.artists = track.artists
        audio.albumartists = track.album_artists

    def _write_track_numbering(self, audio: MediaFile, track: TrackMetadata) -> None:
        """Write track position metadata to audio file.

        Why track numbers matter: Track and total tracks allow music players to
        display position ("Track 3 of 12") and maintain correct playback order.
        This is especially important for albums and compilation playlists.

        Why check for None: Not all tracks have numbering information (e.g., singles,
        tracks extracted from curated playlists). We only write these tags if the
        data is available.

        Args:
            audio: MediaFile instance to modify.
            track: Metadata containing track numbering information.
        """
        if track.track_number is not None:
            audio.track = track.track_number
        if track.total_tracks is not None:
            audio.tracktotal = track.total_tracks

    def _write_year_metadata(self, audio: MediaFile, track: TrackMetadata) -> None:
        """Parse and write release year metadata to audio file.

        Why parse to int: Most audio formats store year as an integer field, not
        a string. We need to convert the string year from YouTube Music (e.g., "2024")
        to an integer.

        Why graceful fallback: If the year field contains unexpected data (e.g.,
        "2024-03-15" or invalid text), we log it but don't fail. Better to have
        a track without a year than to fail the entire tagging operation.

        Args:
            audio: MediaFile instance to modify.
            track: Metadata containing year information.
        """
        if track.year:
            try:
                audio.year = int(track.year)
            except ValueError:
                logger.debug(
                    "Could not parse year '%s' to integer for track '%s'",
                    track.year,
                    track.title,
                )

    def _write_cover_art(self, audio: MediaFile, cover: bytes | None) -> None:
        """Embed cover art image into audio file.

        Why embed cover art: Embedded artwork displays in music players, makes
        libraries more visually appealing, and ensures the art stays with the file
        even if moved to other systems.

        Why mediafile Image class: The Image class automatically detects the image
        format (JPEG vs PNG) from the file's magic bytes and writes the appropriate
        format-specific tags (APIC frame for ID3, PICTURE for Vorbis, etc.).

        Args:
            audio: MediaFile instance to modify.
            cover: Optional cover art bytes (JPEG or PNG format).
        """
        if cover:
            audio.images = [Image(data=cover)]


# ============================================================================
# PUBLIC API - Convenience function for tagging audio files
# ============================================================================


def tag_track(path: Path, track: TrackMetadata, cover: bytes | None = None) -> None:
    """Apply metadata tags to audio file.

    Convenience function that wraps AudioFileTaggingService for simple use cases.

    Args:
        path: Path to the audio file.
        track: Track metadata to apply.
        cover: Optional cover art bytes (JPEG or PNG).

    Raises:
        Exception: If tagging fails (caller should handle gracefully).
    """
    service = AudioFileTaggingService()
    service.apply_metadata_tags(path, track, cover)
