"""Data models for ytmeta.

Public models (domain.py):
    TrackMetadata - Primary output model
    VideoType - Video type enum (ATV/OMV)

Internal models (ytmusic.py):
    Models for parsing ytmusicapi responses. These are implementation
    details and may change if the YouTube Music API changes.
"""

# Public domain models
from ytmeta.models.domain import TrackMetadata, VideoType

# Internal ytmusicapi response models
from ytmeta.models.ytmusic import (
    Album,
    AlbumRef,
    AlbumTrack,
    Artist,
    Playlist,
    PlaylistTrack,
    SearchResult,
    Thumbnail,
)

__all__ = [
    "Album",
    "AlbumRef",
    "AlbumTrack",
    "Artist",
    "Playlist",
    "PlaylistTrack",
    "SearchResult",
    "Thumbnail",
    "TrackMetadata",
    "VideoType",
]
