"""Models for parsing ytmusicapi responses.

These are internal models used to parse and validate responses from
the YouTube Music API. They may change if the API changes.
"""

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
    artists: list[Artist]
    album: AlbumRef | None = None
    thumbnails: list[Thumbnail]
    duration_seconds: int


class Playlist(YTMusicModel):
    """Playlist response from get_playlist()."""

    title: str | None = None
    tracks: list[PlaylistTrack]
    unavailable_count: int = 0  # Tracks without videoId (set by client)


class AlbumTrack(YTMusicModel):
    """Track in an album."""

    video_id: str = Field(alias="videoId")
    title: str
    artists: list[Artist]
    track_number: int = Field(alias="trackNumber")
    duration_seconds: int


class Album(YTMusicModel):
    """Album response from get_album()."""

    title: str
    artists: list[Artist]
    year: str | None = None
    thumbnails: list[Thumbnail]
    tracks: list[AlbumTrack]


class SearchResult(YTMusicModel):
    """Song search result."""

    video_id: str = Field(alias="videoId")
    video_type: str | None = Field(default=None, alias="videoType")
    album: AlbumRef | None = None
