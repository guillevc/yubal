"""Metadata extraction service."""

import logging
from collections.abc import Iterator

from rapidfuzz import process

from yubal.client import YTMusicProtocol
from yubal.models.domain import (
    ContentKind,
    ExtractProgress,
    PlaylistInfo,
    SkipReason,
    TrackMetadata,
    UnavailableTrack,
    VideoType,
)
from yubal.models.ytmusic import Album, AlbumTrack, PlaylistTrack
from yubal.utils.artists import format_artists
from yubal.utils.thumbnails import get_square_thumbnail
from yubal.utils.url import parse_playlist_id

logger = logging.getLogger(__name__)

# Supported video types for download (Audio Track Video and Official Music Video)
SUPPORTED_VIDEO_TYPES = frozenset({VideoType.ATV, VideoType.OMV})

# Fuzzy matching thresholds (using rapidfuzz, scale 0-100)
FUZZY_MATCH_HIGH_CONFIDENCE = 80  # Auto-accept threshold
FUZZY_MATCH_LOW_CONFIDENCE = 50  # Minimum acceptable threshold


class MetadataExtractorService:
    """Service for extracting metadata from YouTube Music playlists.

    Pipeline Overview:
    ==================
    1. extract() - Main entry point: fetches playlist, classifies content type,
                   yields progress updates as tracks are processed
    2. _classify_playlist_as_album_or_playlist() - Determines if OLAK5uy_
                   playlists represent complete albums vs curated playlists
    3. _extract_single_track() - Processes each track: validates video type,
                   searches for album info, builds complete metadata
    4. _match_playlist_track_to_album() - Four-tier matching strategy to find
                   the corresponding album track (video ID → title → duration → fuzzy)
    5. _build_metadata_with_album_info() - Constructs final TrackMetadata using
                   enriched album information
    """

    def __init__(self, client: YTMusicProtocol) -> None:
        """Initialize the service.

        Args:
            client: YouTube Music API client for fetching playlist/album data.
        """
        self._client = client

    # ============================================================================
    # PUBLIC API - Main entry points for metadata extraction
    # ============================================================================

    def extract(
        self, url: str, max_items: int | None = None
    ) -> Iterator[ExtractProgress]:
        """Extract metadata for all tracks in a playlist with progress updates.

        This is the main extraction pipeline. It fetches the playlist, determines
        whether it's a complete album or a curated playlist, then processes each
        track to enrich it with album metadata. Progress updates are yielded as
        each track completes, making this ideal for CLI progress bars or UI updates.

        Why yield progress: Allows callers to display real-time feedback during
        long-running extractions (some playlists have hundreds of tracks).

        Args:
            url: YouTube Music playlist URL.
            max_items: Maximum number of tracks to extract. If None, extracts
                all tracks. Useful for testing or quick previews.

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
        logger.debug("Extracting metadata for playlist: %s", playlist_id)

        playlist = self._client.get_playlist(playlist_id)
        playlist_total = len(playlist.tracks) + playlist.unavailable_count
        unavailable_count = playlist.unavailable_count

        # Apply max_items limit if specified
        tracks = playlist.tracks
        limited = False
        if max_items and max_items < len(playlist.tracks):
            logger.debug("Limiting to %d of %d tracks", max_items, playlist_total)
            tracks = tracks[:max_items]
            # Don't report unavailable count when truncating (outside scope)
            unavailable_count = 0
            limited = True

        total = len(tracks)
        logger.debug(
            "Processing %d tracks (limited=%s, unavailable=%d)",
            total,
            limited,
            unavailable_count,
        )

        # Classify content: determines if OLAK5uy_ playlist is a complete album
        # (all tracks from one album) or a curated playlist (e.g., "Top songs")
        kind = self._classify_playlist_as_album_or_playlist(
            playlist_id, playlist.tracks
        )

        # Convert raw unavailable track dicts to domain models
        unavailable_tracks = [
            UnavailableTrack(
                title=raw.get("title"),
                artists=raw.get("artists", []),
                album=raw.get("album"),
                reason=SkipReason(raw["reason"]),
            )
            for raw in playlist.unavailable_tracks_raw
        ]

        # Get unavailable tracks (only include when not limited)
        unavailable_for_info: list[UnavailableTrack] = (
            [] if limited else unavailable_tracks
        )

        playlist_info = PlaylistInfo(
            playlist_id=playlist_id,
            title=playlist.title,
            cover_url=get_square_thumbnail(playlist.thumbnails),
            kind=kind,
            author=playlist.author.name if playlist.author else None,
            unavailable_tracks=unavailable_for_info,
        )

        extracted_count = 0
        skipped_by_reason: dict[SkipReason, int] = {}

        # Add unavailable tracks from playlist by reason
        for ut in unavailable_tracks:
            if not limited:  # Only count when not limiting
                skipped_by_reason[ut.reason] = skipped_by_reason.get(ut.reason, 0) + 1

        for track in tracks:
            try:
                metadata = self._extract_single_track(track)
            except Exception as e:
                logger.exception(
                    "Failed to extract track '%s': %s",
                    track.title,
                    e,
                )
                # Continue with partial results instead of failing entirely
                metadata = self._create_fallback_metadata(track)

            # Skip tracks that return None (unsupported video types)
            if metadata is None:
                skipped_by_reason[SkipReason.UNSUPPORTED_VIDEO_TYPE] = (
                    skipped_by_reason.get(SkipReason.UNSUPPORTED_VIDEO_TYPE, 0) + 1
                )
                logger.debug(
                    "Skipped track '%s': unsupported video type",
                    track.title,
                )
                continue

            extracted_count += 1
            yield ExtractProgress(
                current=extracted_count,
                total=total,
                playlist_total=playlist_total,
                skipped_by_reason=skipped_by_reason.copy(),
                track=metadata,
                playlist_info=playlist_info,
            )

        # Log with stats_type discriminator and skipped_by_reason dict
        # Note: failed=0 because extraction failures become fallback metadata
        # rather than stopping the process. Skipped tracks are the meaningful metric.
        logger.debug(
            "Extraction complete: %d extracted, %d skipped",
            extracted_count,
            sum(skipped_by_reason.values()),
        )

    def extract_all(
        self, url: str, max_items: int | None = None
    ) -> list[TrackMetadata]:
        """Extract metadata for all tracks, returning complete results at once.

        Convenience wrapper around extract() for cases where you don't need
        incremental progress updates. Simply collects all results and returns
        them as a list.

        Args:
            url: YouTube Music playlist URL.
            max_items: Maximum number of tracks to extract. If None, extracts
                all tracks.

        Returns:
            List of extracted track metadata.

        Raises:
            PlaylistParseError: If URL is invalid.
            PlaylistNotFoundError: If playlist doesn't exist.
            APIError: If API requests fail.
        """
        return [p.track for p in self.extract(url, max_items=max_items)]

    # ============================================================================
    # CONTENT CLASSIFICATION - Distinguish albums from curated playlists
    # ============================================================================

    def _classify_playlist_as_album_or_playlist(
        self, playlist_id: str, tracks: list[PlaylistTrack]
    ) -> ContentKind:
        """Classify playlist as a complete album vs a curated playlist.

        Why this matters: YouTube Music creates playlists for both complete albums
        (all tracks from one album) and curated collections (e.g., "Top songs from
        artist"). We need to distinguish these because they require different
        metadata handling strategies.

        Classification strategy (5 checks, all must pass):
        1. OLAK5uy_ prefix - YouTube's album playlist identifier
        2. Has tracks - Not empty
        3. Single album reference - All tracks point to same album ID
        4. Album exists - Can fetch the album from YouTube Music
        5. Complete match - Playlist contains ALL tracks from the album

        Why so strict: Prevents false positives like "Greatest Hits" playlists
        that contain a subset of tracks from a single album.

        Args:
            playlist_id: The playlist ID to classify.
            tracks: List of tracks in the playlist.

        Returns:
            ContentKind.ALBUM if complete album, ContentKind.PLAYLIST otherwise.
        """
        # Check 1: Must have OLAK5uy_ prefix (album playlist format)
        if not playlist_id.startswith("OLAK5uy_"):
            logger.debug("Not an album: missing OLAK5uy_ prefix")
            return ContentKind.PLAYLIST

        # Check 2: Must have tracks
        if not tracks:
            logger.debug("Not an album: no tracks")
            return ContentKind.PLAYLIST

        # Check 3: All tracks must reference the same album
        album_ids = {t.album.id for t in tracks if t.album and t.album.id}
        logger.debug("Album IDs found on tracks: %s", album_ids)

        if len(album_ids) != 1:
            logger.debug(
                "Not an album: tracks reference %d different albums", len(album_ids)
            )
            return ContentKind.PLAYLIST

        # Check 4: Fetch the album to verify all tracks are present
        album_id = next(iter(album_ids))
        try:
            album = self._client.get_album(album_id)
        except Exception as e:
            logger.debug("Not an album: failed to fetch album %s: %s", album_id, e)
            return ContentKind.PLAYLIST

        # Check 5: Playlist must contain all album tracks
        matched_album_tracks: set[str] = set()

        for playlist_track in tracks:
            album_track = self._match_playlist_track_to_album(album, playlist_track)
            if album_track:
                matched_album_tracks.add(album_track.video_id)

        matched_count = len(matched_album_tracks)
        logger.debug(
            "Album track matching: %d/%d matched",
            matched_count,
            len(album.tracks),
        )

        if matched_count == len(album.tracks):
            logger.debug("Detected complete album: %s", album.title)
            return ContentKind.ALBUM

        logger.debug(
            "Not an album: matched %d/%d tracks", matched_count, len(album.tracks)
        )
        return ContentKind.PLAYLIST

    # ============================================================================
    # SINGLE TRACK EXTRACTION - Process individual tracks and enrich with album data
    # ============================================================================

    def _extract_single_track(self, track: PlaylistTrack) -> TrackMetadata | None:
        """Extract and enrich metadata for a single track.

        This is the core per-track processing pipeline:
        1. Validate video type (skip unsupported types like UGC videos)
        2. Find album info (from track data or search)
        3. Fetch full album details from YouTube Music
        4. Build enriched metadata with album info, or fallback to basic data

        Why search for albums: Some playlist tracks don't include album IDs,
        so we search YouTube Music to find the corresponding album. This ensures
        we get complete metadata (track numbers, year, album artists, etc).

        Args:
            track: Playlist track to process.

        Returns:
            Extracted track metadata, or None if track should be skipped
            (e.g., unsupported video type).
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

        # Build enriched metadata from album, or fallback to basic metadata
        if album:
            return self._build_metadata_with_album_info(
                track, album, video_type, search_atv_id
            )
        return self._create_fallback_metadata(track, video_type)

    # ============================================================================
    # VIDEO TYPE VALIDATION - Ensure track is a supported format
    # ============================================================================

    def _determine_video_type(self, track: PlaylistTrack) -> VideoType | None:
        """Validate and determine the video type from track information.

        Why this matters: YouTube Music has different video types (ATV = Audio Track
        Video, OMV = Official Music Video, UGC = User Generated Content, etc).
        We only support ATV and OMV because they have reliable metadata. UGC videos
        often have incorrect or missing metadata.

        Args:
            track: Playlist track to check.

        Returns:
            VideoType enum value if supported, or None if missing/unsupported.
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

    # ============================================================================
    # ALBUM DISCOVERY - Search for album info when not directly available
    # ============================================================================

    def _search_for_album(self, track: PlaylistTrack) -> tuple[str | None, str | None]:
        """Search YouTube Music to find album information for a track.

        Why search: Some playlist tracks don't include album IDs in their metadata.
        Searching allows us to find the canonical album and enrich the track with
        complete metadata (track numbers, album artists, release year, etc).

        Search strategy: Query using "artist + title" and take the first result
        with album information. Also captures the ATV video ID from search results
        for tracks that are OMVs in the playlist (gives us both video variants).

        Args:
            track: Track to search for.

        Returns:
            Tuple of (album_id, atv_video_id) if found, (None, None) otherwise.
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

    # ============================================================================
    # TRACK MATCHING - Four-tier strategy to match playlist tracks to album tracks
    # ============================================================================

    def _match_playlist_track_to_album(
        self, album: Album, track: PlaylistTrack
    ) -> AlbumTrack | None:
        """Match a playlist track to its album track using 4-tier strategy.

        Why this is complex: Playlist tracks and album tracks may have different
        video IDs, slightly different titles (e.g., "Song" vs "Song (Remaster)"),
        or other variations. We need multiple fallback strategies to reliably
        match them.

        Matching tiers (in order of reliability):
        1. Video ID match - Most reliable, matches exact video
        2. Title match (exact) - Case-insensitive exact title match
        3. Duration match - If only one album track has matching duration
        4. Fuzzy title match - Uses similarity algorithm (50-80% threshold)

        Why four tiers: Balances accuracy (avoiding false matches) with coverage
        (successfully matching as many tracks as possible).

        Args:
            album: Album to search in.
            track: Playlist track to find in album.

        Returns:
            Matching album track or None if no confident match found.
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
        """Match track using fuzzy string similarity (tier 4 fallback).

        Why fuzzy matching: Handles minor title variations like:
        - "Song (Remastered)" vs "Song"
        - "Song - Live" vs "Song (Live)"
        - Typos or punctuation differences

        Uses rapidfuzz library with confidence thresholds:
        - >80% score: High confidence, accept silently
        - 50-80% score: Medium confidence, accept with warning
        - <50% score: Low confidence, reject to avoid false matches

        Why two thresholds: >80% catches obvious matches like "Song (2024 Remaster)"
        vs "Song". 50-80% catches fuzzier matches but warns the user in case it's
        a false positive. <50% is rejected because it's likely a different track.

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

        if score > FUZZY_MATCH_HIGH_CONFIDENCE:
            return candidates[matched_title]

        if score > FUZZY_MATCH_LOW_CONFIDENCE:
            logger.warning(
                "Fuzzy match: '%s' -> '%s' (%.0f%%)",
                title,
                matched_title,
                score,
            )
            return candidates[matched_title]

        # Low confidence - reject
        logger.warning(
            "No confident match for '%s' (best: '%s' @ %.0f%%)",
            title,
            matched_title,
            score,
        )
        return None

    # ============================================================================
    # METADATA CONSTRUCTION - Build final TrackMetadata objects
    # ============================================================================

    def _resolve_video_ids(
        self,
        playlist_video_id: str,
        album_video_id: str | None,
        video_type: VideoType,
        search_atv_id: str | None,
    ) -> tuple[str | None, str | None]:
        """Resolve OMV and ATV video IDs from multiple sources.

        Why this matters: Tracks can have two video variants (OMV and ATV), and
        we want to capture both when possible. This allows users to choose their
        preferred format during download (audio track vs music video).

        Resolution logic:
        - If playlist track is ATV: use it directly, get OMV from album
        - If playlist track is OMV: use it, get ATV from search results

        Why check if IDs are different: Sometimes album returns the same video ID
        for both variants. We only store OMV if it's actually different from ATV.

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

    def _build_metadata_with_album_info(
        self,
        track: PlaylistTrack,
        album: Album,
        video_type: VideoType,
        search_atv_id: str | None,
    ) -> TrackMetadata:
        """Build enriched track metadata using album information.

        This is where we combine playlist track data with album data to create
        complete, accurate metadata. Album info provides:
        - Track numbers and total tracks
        - Album artists (may differ from track artists)
        - Release year
        - High-quality album art
        - Canonical track titles

        Why prefer album data: Album metadata is more authoritative and complete
        than playlist metadata. If we can't match the track to the album, we
        fall back to the original playlist track data.

        Args:
            track: Original playlist track.
            album: Album containing the track.
            video_type: Source video type (ATV or OMV).
            search_atv_id: ATV video ID from search (if any).

        Returns:
            Complete track metadata with album information.
        """
        album_track = self._match_playlist_track_to_album(album, track)

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
        """Create basic metadata when album information is unavailable.

        Why fallback: If we can't find album info (search failed, album doesn't
        exist, API errors), we still want to extract what we can from the
        playlist track itself. This ensures the user gets something rather than
        nothing.

        Fallback limitations (missing data):
        - No track numbers
        - No total tracks
        - No release year
        - No album artists (uses track artists instead)
        - Lower quality album art

        Args:
            track: Playlist track to create fallback from.
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
