"""Metadata extraction from YouTube Music playlists."""

import re

from ytmusicapi import YTMusic

from ytmeta.models import TrackMetadata, VideoType
from ytmeta.ytmusic_models import (
    Album,
    AlbumTrack,
    Artist,
    Playlist,
    PlaylistTrack,
    SearchResult,
    Thumbnail,
)


def parse_playlist_id(url: str) -> str:
    """Extract playlist ID from YouTube Music URL."""
    if match := re.search(r"list=([A-Za-z0-9_-]+)", url):
        return match.group(1)
    raise ValueError(f"Could not extract playlist ID from: {url}")


def format_artists(artists: list[Artist]) -> str:
    """Format artists list as 'Artist One; Artist Two'."""
    if not artists:
        return ""
    return "; ".join(a.name for a in artists if a.name)


def get_square_thumbnail(thumbnails: list[Thumbnail]) -> str | None:
    """Get the largest square thumbnail URL."""
    if not thumbnails:
        return None
    # Filter for square thumbnails and get largest
    square = [t for t in thumbnails if t.width == t.height]
    if square:
        return max(square, key=lambda t: t.width).url
    # Fallback to any thumbnail
    return thumbnails[-1].url if thumbnails else None


def find_track_in_album(album: Album, track: PlaylistTrack) -> AlbumTrack | None:
    """Find a track in album by title or duration."""
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


def extract_metadata(ytm: YTMusic, url: str) -> list[TrackMetadata]:
    """Extract metadata for all tracks in a playlist."""
    playlist_data = ytm.get_playlist(parse_playlist_id(url), limit=None)
    # Filter out unavailable tracks (no videoId) before validation
    raw_tracks = playlist_data.get("tracks") or []
    playlist_data["tracks"] = [t for t in raw_tracks if t and t.get("videoId")]
    playlist = Playlist.model_validate(playlist_data)
    results = []

    for track in playlist.tracks:
        video_type_raw = track.video_type or ""
        video_type = VideoType.ATV if "ATV" in video_type_raw else VideoType.OMV
        album_id = track.album.id if track.album else None
        search_atv_id = None  # ATV found via search (for OMV tracks)

        # For OMV without album, search for the track
        if not album_id:
            artists = format_artists(track.artists)
            query = f"{artists} {track.title}".strip()
            if query:
                search_data = ytm.search(
                    query, filter="songs", limit=1, ignore_spelling=True
                )
                search_results = [SearchResult.model_validate(r) for r in search_data]
                # Find first result with album info
                for result in search_results:
                    if result.album:
                        album_id = result.album.id
                        # Capture ATV videoId from search result
                        if result.video_type == "MUSIC_VIDEO_TYPE_ATV":
                            search_atv_id = result.video_id
                        break

        # Get album details
        album: Album | None = None
        if album_id:
            album_data = ytm.get_album(album_id)
            album = Album.model_validate(album_data)

        if album:
            # Try to find track in album for track number
            album_track = find_track_in_album(album, track)

            # Use album track info if found, otherwise use original track info
            track_title = album_track.title if album_track else track.title
            track_artists = album_track.artists if album_track else track.artists
            track_number = album_track.track_number if album_track else None

            # OMV from album track, ATV from playlist (if ATV) or search
            omv_id = album_track.video_id if album_track else None
            atv_id = track.video_id if video_type == VideoType.ATV else search_atv_id

            meta = TrackMetadata(
                omv_video_id=omv_id or track.video_id,  # Fallback to source if no match
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
        else:
            # Fallback: use track info directly (must be OMV since ATV has album)
            meta = TrackMetadata(
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

        results.append(meta)

    return results
