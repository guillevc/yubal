"""Metadata extraction service."""

import logging
from collections.abc import Iterator

from rapidfuzz import process

from yubal.client import YTMusicProtocol
from yubal.models.domain import (
    ContentKind,
    ExtractProgress,
    PlaylistInfo,
    TrackMetadata,
    VideoType,
)
from yubal.models.ytmusic import Album, AlbumTrack, PlaylistTrack
from yubal.utils import (
    format_artists,
    get_square_thumbnail,
    is_album_playlist,
    parse_playlist_id,
)

logger = logging.getLogger(__name__)

# Supported video types for download
SUPPORTED_VIDEO_TYPES = {VideoType.ATV, VideoType.OMV}


class MetadataExtractorService:
    """Service for extracting metadata from YouTube Music playlists.

    This service orchestrates the extraction process:
    1. Fetch playlist
    2. For each track, resolve album info
    3. Build structured metadata
    """

    def __init__(self, client: YTMusicProtocol) -> None:
        """Initialize the service.

        Args:
            client: YouTube Music API client.
        """
        self._client = client

    def extract(
        self, url: str, max_items: int | None = None
    ) -> Iterator[ExtractProgress]:
        """Extract metadata for all tracks in a playlist.

        Yields progress updates as each track is processed. Use extract_all()
        for a simpler interface that returns all results at once.

        Args:
            url: YouTube Music playlist URL.
            max_items: Maximum number of tracks to extract. Only applies to
                playlists, not albums. If None, extracts all tracks.

        Yields:
            ExtractProgress with current/total counts and the extracted track.
            The track field may be a fallback if extraction failed for that track.

        Raises:
            PlaylistParseError: If URL is invalid.
            PlaylistNotFoundError: If playlist doesn't exist.
            APIError: If API requests fail.

        Example:
            >>> for progress in extractor.extract(url):
            ...     print(f"[{progress.current}/{progress.total}]")
        """
        playlist_id = parse_playlist_id(url)
        logger.info("Extracting metadata for playlist: %s", playlist_id)

        playlist = self._client.get_playlist(playlist_id)
        playlist_total = len(playlist.tracks) + playlist.unavailable_count
        unavailable_count = playlist.unavailable_count

        # Apply max_items limit only to playlists, not albums
        tracks = playlist.tracks
        limited = False
        if max_items and not is_album_playlist(playlist_id):
            if max_items < len(playlist.tracks):
                logger.info("Limiting to %d of %d tracks", max_items, playlist_total)
                tracks = tracks[:max_items]
            limited = True
            # Don't report unavailable count when limiting (outside scope)
            unavailable_count = 0

        total = len(tracks)
        if limited:
            logger.info("Processing %d tracks (limited from %d)", total, playlist_total)
        else:
            logger.info(
                "Found %d tracks in playlist (%d unavailable)",
                total,
                unavailable_count,
            )

        # Create playlist info for progress updates
        kind = (
            ContentKind.ALBUM
            if is_album_playlist(playlist_id)
            else ContentKind.PLAYLIST
        )
        playlist_info = PlaylistInfo(
            playlist_id=playlist_id,
            title=playlist.title,
            cover_url=get_square_thumbnail(playlist.thumbnails),
            kind=kind,
        )

        extracted_count = 0
        skipped_count = 0

        for track in tracks:
            try:
                metadata = self._extract_track(track)
            except Exception as e:
                logger.warning(
                    "Failed to extract track '%s': %s",
                    track.title,
                    e,
                )
                # Continue with partial results instead of failing entirely
                metadata = self._create_fallback_metadata(track)

            # Skip tracks that return None (unsupported video types)
            if metadata is None:
                skipped_count += 1
                continue

            extracted_count += 1
            yield ExtractProgress(
                current=extracted_count,
                total=total,
                playlist_total=playlist_total,
                skipped=skipped_count,
                unavailable=unavailable_count,
                track=metadata,
                playlist_info=playlist_info,
            )

        logger.info(
            "Extracted metadata for %d tracks (%d skipped, %d unavailable)",
            extracted_count,
            skipped_count,
            unavailable_count,
        )

    def extract_all(
        self, url: str, max_items: int | None = None
    ) -> list[TrackMetadata]:
        """Extract metadata for all tracks in a playlist.

        Convenience method that collects all results from extract().

        Args:
            url: YouTube Music playlist URL.
            max_items: Maximum number of tracks to extract. Only applies to
                playlists, not albums. If None, extracts all tracks.

        Returns:
            List of extracted track metadata.

        Raises:
            PlaylistParseError: If URL is invalid.
            PlaylistNotFoundError: If playlist doesn't exist.
            APIError: If API requests fail.
        """
        return [p.track for p in self.extract(url, max_items=max_items)]

    def _extract_track(self, track: PlaylistTrack) -> TrackMetadata | None:
        """Extract metadata for a single track.

        Args:
            track: Playlist track to process.

        Returns:
            Extracted track metadata, or None if track should be skipped.
        """
        video_type = self._determine_video_type(track)

        # Skip tracks with unsupported video type (warning already logged)
        if video_type is None:
            return None

        album_id = track.album.id if track.album else None
        search_atv_id: str | None = None

        # For tracks without album, search for album info
        if not album_id:
            album_id, search_atv_id = self._search_for_album(track)

        # Fetch album details if we have an ID
        album: Album | None = None
        if album_id:
            try:
                album = self._client.get_album(album_id)
            except Exception as e:
                logger.debug("Failed to fetch album %s: %s", album_id, e)

        # Build metadata from album or fallback
        if album:
            return self._build_metadata_from_album(
                track, album, video_type, search_atv_id
            )
        return self._create_fallback_metadata(track, video_type)

    def _determine_video_type(self, track: PlaylistTrack) -> VideoType | None:
        """Determine the video type from track info.

        Args:
            track: Playlist track.

        Returns:
            VideoType enum value, or None if missing/unsupported.
        """
        if not track.video_type:
            logger.warning(
                "Missing video type for track '%s'",
                track.title,
            )
            return None

        try:
            video_type = VideoType(track.video_type)
        except ValueError:
            logger.warning(
                "Unknown video type '%s' for track '%s'",
                track.video_type,
                track.title,
            )
            return None

        # Only ATV and OMV are supported
        if video_type not in SUPPORTED_VIDEO_TYPES:
            logger.warning(
                "Unsupported video type '%s' for track '%s'",
                video_type.name,
                track.title,
            )
            return None

        return video_type

    def _search_for_album(self, track: PlaylistTrack) -> tuple[str | None, str | None]:
        """Search for album info for a track.

        Args:
            track: Track to search for.

        Returns:
            Tuple of (album_id, atv_video_id) if found.
        """
        artists = format_artists(track.artists)
        query = f"{artists} {track.title}".strip()

        if not query:
            return None, None

        try:
            results = self._client.search_songs(query)
        except Exception as e:
            logger.debug("Search failed for '%s': %s", query, e)
            return None, None

        for result in results:
            if result.album:
                atv_id = result.video_id if result.video_type == VideoType.ATV else None
                return result.album.id, atv_id

        return None, None

    def _find_track_in_album(
        self, album: Album, track: PlaylistTrack
    ) -> AlbumTrack | None:
        """Find a track in album by video_id, title, duration, or fuzzy title match.

        Args:
            album: Album to search in.
            track: Track to find.

        Returns:
            Matching album track or None.
        """
        target_video_id = track.video_id
        target_title = track.title.lower().strip()
        target_duration = track.duration_seconds

        # First try: match by video_id (most reliable)
        for album_track in album.tracks:
            if album_track.video_id == target_video_id:
                return album_track

        # Second try: match by title (exact, case-insensitive)
        for album_track in album.tracks:
            if album_track.title.lower().strip() == target_title:
                return album_track

        # Third try: match by duration if unique
        if target_duration:
            matches = [t for t in album.tracks if t.duration_seconds == target_duration]
            if len(matches) == 1:
                return matches[0]

        # Fourth try: fuzzy title match using rapidfuzz
        return self._find_track_by_fuzzy_title(album, track.title)

    def _find_track_by_fuzzy_title(self, album: Album, title: str) -> AlbumTrack | None:
        """Find a track using fuzzy/similarity title matching.

        Uses rapidfuzz to find the best matching track title.
        Returns the match if similarity is above 50%, with a warning for
        scores between 50-80%.

        Args:
            album: Album to search in.
            title: Title to match against.

        Returns:
            Best matching album track or None if no confident match.
        """
        if not album.tracks:
            return None

        # Build a mapping from title to track for lookup
        candidates: dict[str, AlbumTrack] = {t.title: t for t in album.tracks}

        result = process.extractOne(title, candidates.keys())
        if not result:
            return None

        matched_title, score, _ = result

        if score > 80:
            # High confidence - auto-accept
            return candidates[matched_title]
        elif score > 50:
            # Medium confidence - warn but use it
            logger.warning(
                "Fuzzy match: '%s' -> '%s' (%.0f%%)",
                title,
                matched_title,
                score,
            )
            return candidates[matched_title]
        else:
            # Low confidence - too risky
            logger.warning(
                "No confident match for '%s' (best: '%s' @ %.0f%%)",
                title,
                matched_title,
                score,
            )
            return None

    def _resolve_video_ids(
        self,
        playlist_video_id: str,
        album_video_id: str | None,
        video_type: VideoType,
        search_atv_id: str | None,
    ) -> tuple[str | None, str | None]:
        """Resolve OMV and ATV video IDs from available sources.

        Args:
            playlist_video_id: Video ID from the playlist track.
            album_video_id: Video ID from the album track (if found).
            video_type: Whether the playlist track is ATV or OMV.
            search_atv_id: ATV video ID from search results (if any).

        Returns:
            Tuple of (omv_video_id, atv_video_id).
        """
        if video_type == VideoType.ATV:
            # Playlist track is ATV
            atv_id = playlist_video_id
            # OMV comes from album, but only if different from ATV
            omv_id = album_video_id if album_video_id != atv_id else None
        else:
            # Playlist track is OMV
            omv_id = album_video_id or playlist_video_id
            atv_id = search_atv_id

        return omv_id, atv_id

    def _build_metadata_from_album(
        self,
        track: PlaylistTrack,
        album: Album,
        video_type: VideoType,
        search_atv_id: str | None,
    ) -> TrackMetadata:
        """Build track metadata using album information.

        Args:
            track: Original playlist track.
            album: Album containing the track.
            video_type: Source video type.
            search_atv_id: ATV video ID from search (if any).

        Returns:
            Complete track metadata.
        """
        album_track = self._find_track_in_album(album, track)

        # Use album track info if found, otherwise use original track info
        track_title = album_track.title if album_track else track.title
        track_artists = album_track.artists if album_track else track.artists
        track_number = album_track.track_number if album_track else None

        # Resolve video IDs
        album_video_id = album_track.video_id if album_track else None
        omv_id, atv_id = self._resolve_video_ids(
            playlist_video_id=track.video_id,
            album_video_id=album_video_id,
            video_type=video_type,
            search_atv_id=search_atv_id,
        )

        return TrackMetadata(
            omv_video_id=omv_id,
            atv_video_id=atv_id,
            title=track_title,
            artists=[a.name for a in track_artists],
            album=album.title,
            album_artists=[a.name for a in album.artists],
            track_number=track_number,
            total_tracks=len(album.tracks) if album.tracks else None,
            year=album.year,
            cover_url=get_square_thumbnail(album.thumbnails),
            video_type=video_type,
        )

    def _create_fallback_metadata(
        self,
        track: PlaylistTrack,
        video_type: VideoType | None = None,
    ) -> TrackMetadata | None:
        """Create fallback metadata when album info is unavailable.

        Args:
            track: Playlist track.
            video_type: Optional video type (determined if not provided).

        Returns:
            Basic track metadata, or None if video type is unsupported.
        """
        if video_type is None:
            video_type = self._determine_video_type(track)

        # Skip unsupported video types
        # None means unknown/unsupported from _determine_video_type
        if video_type is None or video_type not in SUPPORTED_VIDEO_TYPES:
            return None

        # Assign video ID based on track type
        if video_type == VideoType.ATV:
            omv_id = None
            atv_id = track.video_id
        else:
            omv_id = track.video_id
            atv_id = None

        return TrackMetadata(
            omv_video_id=omv_id,
            atv_video_id=atv_id,
            title=track.title,
            artists=[a.name for a in track.artists],
            album=track.album.name if track.album else "",
            album_artists=[a.name for a in track.artists],
            track_number=None,
            total_tracks=None,
            year=None,
            cover_url=get_square_thumbnail(track.thumbnails),
            video_type=video_type,
        )
