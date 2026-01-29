"""Models for parsing ytmusicapi responses.

These are internal models used to parse and validate responses from
the YouTube Music API. They may change if the API changes.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "Album",
    "AlbumRef",
    "AlbumTrack",
    "Artist",
    "Playlist",
    "PlaylistTrack",
    "SearchResult",
    "Thumbnail",
]


class YTMusicModel(BaseModel):
    """Base model for ytmusicapi responses."""

    model_config = ConfigDict(extra="ignore", frozen=True)


class Thumbnail(YTMusicModel):
    """Video/album thumbnail."""

    url: str
    width: int
    height: int


class Artist(YTMusicModel):
    """Artist reference."""

    name: str
    id: str | None = None


class AlbumRef(YTMusicModel):
    """Album reference (in playlist/search results)."""

    id: str
    name: str


class PlaylistTrack(YTMusicModel):
    """Track in a playlist."""

    video_id: str = Field(alias="videoId")
    video_type: str | None = Field(default=None, alias="videoType")
    title: str
    artists: list[Artist] = Field(default_factory=list)
    album: AlbumRef | None = None
    thumbnails: list[Thumbnail] = Field(default_factory=list)
    duration_seconds: int


class Playlist(YTMusicModel):
    """Playlist response from get_playlist()."""

    title: str | None = None
    thumbnails: list[Thumbnail] = Field(default_factory=list)
    tracks: list[PlaylistTrack]
    unavailable_tracks_raw: list[dict[str, Any]] = Field(
        default_factory=list, alias="unavailable_tracks"
    )
    author: Artist | None = None  # Channel/creator name

    @property
    def unavailable_count(self) -> int:
        """Number of unavailable tracks in the playlist."""
        return len(self.unavailable_tracks_raw)


class AlbumTrack(YTMusicModel):
    """Track in an album."""

    video_id: str | None = Field(default=None, alias="videoId")
    title: str
    artists: list[Artist] = Field(default_factory=list)
    track_number: int | None = Field(default=None, alias="trackNumber")
    duration_seconds: int | None = None
    duration: str | None = None



class Album(YTMusicModel):
    """Album response from get_album()."""

    title: str
    artists: list[Artist]
    year: str | None = None
    thumbnails: list[Thumbnail]
    tracks: list[AlbumTrack]
    audio_playlist_id: str | None = Field(default=None, alias="audioPlaylistId")
    track_count: int | None = Field(default=None, alias="trackCount")
    duration: str | None = None
    description: str | None = None


class SearchResult(YTMusicModel):
    """Song search result."""

    video_id: str = Field(alias="videoId")
    video_type: str | None = Field(default=None, alias="videoType")
    title: str
    artists: list[Artist] = Field(default_factory=list)
    album: AlbumRef | None = None
