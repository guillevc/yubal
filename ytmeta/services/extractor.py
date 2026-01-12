"""Metadata extraction service."""

import asyncio
import logging
from collections.abc import Callable

from ytmeta.client import YTMusicProtocol
from ytmeta.models.domain import TrackMetadata, VideoType
from ytmeta.models.ytmusic import Album, AlbumTrack, PlaylistTrack
from ytmeta.utils import format_artists, get_square_thumbnail, parse_playlist_id

logger = logging.getLogger(__name__)

# Raw video type string for ATV
VIDEO_TYPE_ATV = "MUSIC_VIDEO_TYPE_ATV"


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
        self,
        url: str,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[TrackMetadata]:
        """Extract metadata for all tracks in a playlist.

        Args:
            url: YouTube Music playlist URL.
            on_progress: Optional callback for progress updates (current, total).

        Returns:
            List of extracted track metadata.

        Raises:
            PlaylistParseError: If URL is invalid.
            PlaylistNotFoundError: If playlist doesn't exist.
            APIError: If API requests fail.
        """
        playlist_id = parse_playlist_id(url)
        logger.info("Extracting metadata for playlist: %s", playlist_id)

        playlist = self._client.get_playlist(playlist_id)
        total = len(playlist.tracks)
        logger.info("Found %d tracks in playlist", total)

        results: list[TrackMetadata] = []

        for i, track in enumerate(playlist.tracks):
            if on_progress:
                on_progress(i + 1, total)

            try:
                metadata = self._extract_track(track)
                results.append(metadata)
            except Exception as e:
                logger.warning(
                    "Failed to extract track '%s': %s",
                    track.title,
                    e,
                )
                # Continue with partial results instead of failing entirely
                results.append(self._create_fallback_metadata(track))

        logger.info("Extracted metadata for %d tracks", len(results))
        return results

    def _extract_track(self, track: PlaylistTrack) -> TrackMetadata:
        """Extract metadata for a single track.

        Args:
            track: Playlist track to process.

        Returns:
            Extracted track metadata.
        """
        video_type = self._determine_video_type(track)
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

    def _determine_video_type(self, track: PlaylistTrack) -> VideoType:
        """Determine the video type from track info.

        Args:
            track: Playlist track.

        Returns:
            VideoType enum value.
        """
        video_type_raw = track.video_type or ""
        return VideoType.ATV if "ATV" in video_type_raw else VideoType.OMV

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
                atv_id = (
                    result.video_id if result.video_type == VIDEO_TYPE_ATV else None
                )
                return result.album.id, atv_id

        return None, None

    def _find_track_in_album(
        self, album: Album, track: PlaylistTrack
    ) -> AlbumTrack | None:
        """Find a track in album by title or duration.

        Args:
            album: Album to search in.
            track: Track to find.

        Returns:
            Matching album track or None.
        """
        target_title = track.title.lower().strip()
        target_duration = track.duration_seconds

        # First try: match by title
        for album_track in album.tracks:
            if album_track.title.lower().strip() == target_title:
                return album_track

        # Second try: match by duration if unique
        if target_duration:
            matches = [t for t in album.tracks if t.duration_seconds == target_duration]
            if len(matches) == 1:
                return matches[0]

        return None

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

        # OMV from album track, ATV from playlist (if ATV) or search
        omv_id = album_track.video_id if album_track else None
        atv_id = track.video_id if video_type == VideoType.ATV else search_atv_id

        return TrackMetadata(
            omv_video_id=omv_id or track.video_id,
            atv_video_id=atv_id,
            title=track_title,
            artist=format_artists(track_artists),
            album=album.title,
            albumartist=format_artists(album.artists),
            tracknumber=track_number,
            year=album.year,
            cover_url=get_square_thumbnail(album.thumbnails),
            video_type=video_type,
        )

    def _create_fallback_metadata(
        self,
        track: PlaylistTrack,
        video_type: VideoType | None = None,
    ) -> TrackMetadata:
        """Create fallback metadata when album info is unavailable.

        Args:
            track: Playlist track.
            video_type: Optional video type (determined if not provided).

        Returns:
            Basic track metadata.
        """
        if video_type is None:
            video_type = self._determine_video_type(track)

        return TrackMetadata(
            omv_video_id=track.video_id,
            atv_video_id=None,
            title=track.title,
            artist=format_artists(track.artists),
            album=track.album.name if track.album else "",
            albumartist=format_artists(track.artists),
            tracknumber=None,
            year=None,
            cover_url=get_square_thumbnail(track.thumbnails),
            video_type=video_type,
        )

    async def extract_async(
        self,
        url: str,
        on_progress: Callable[[int, int], None] | None = None,
    ) -> list[TrackMetadata]:
        """Async version of extract() for use with FastAPI/async frameworks.

        Runs the synchronous extract() in a thread pool to avoid blocking
        the event loop. Use this method in async contexts.

        Args:
            url: YouTube Music playlist URL.
            on_progress: Optional callback for progress updates (current, total).

        Returns:
            List of extracted track metadata.

        Raises:
            PlaylistParseError: If URL is invalid.
            PlaylistNotFoundError: If playlist doesn't exist.
            APIError: If API requests fail.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,  # Use default executor
            self.extract,
            url,
            on_progress,
        )
