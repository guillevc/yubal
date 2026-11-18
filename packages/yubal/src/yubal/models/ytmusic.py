"""Models for parsing ytmusicapi responses.

These are internal models used to parse and validate responses from
the YouTube Music API. They may change if the API changes.
"""

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

__all__ = [
    "Album",
    "AlbumRef",
    "AlbumTrack",
    "Artist",
    "ArtistDiscography",
    "ArtistRelease",
    "ArtistSearchResult",
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

    id: str | None = None
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
    year: str | None = None

    @property
    def unavailable_count(self) -> int:
        """Number of unavailable tracks in the playlist."""
        return len(self.unavailable_tracks_raw)


class AlbumTrack(YTMusicModel):
    """Track in an album."""

    video_id: str = Field(alias="videoId")
    title: str
    artists: list[Artist] = Field(default_factory=list)
    track_number: int = Field(alias="trackNumber")
    duration_seconds: int


class Album(YTMusicModel):
    """Album response from get_album()."""

    title: str
    artists: list[Artist]
    year: str | None = None
    thumbnails: list[Thumbnail]
    tracks: list[AlbumTrack]
    audio_playlist_id: str | None = Field(default=None, alias="audioPlaylistId")


class SearchResult(YTMusicModel):
    """Song search result."""

    video_id: str = Field(alias="videoId")
    video_type: str | None = Field(default=None, alias="videoType")
    title: str
    artists: list[Artist] = Field(default_factory=list)
    album: AlbumRef | None = None


class ArtistSearchResult(YTMusicModel):
    """Artist result from search(filter="artists")."""

    browse_id: str = Field(alias="browseId")  # Artist channel ID (UC...)
    artist: str
    thumbnails: list[Thumbnail] = Field(default_factory=list)


class ArtistRelease(YTMusicModel):
    """Album or single listed on an artist page.

    get_artist() returns ``audioPlaylistId`` for albums (not singles), while
    get_artist_albums() returns ``playlistId``. Both are the OLAK5uy_ album
    playlist ID, so either is accepted.
    """

    title: str
    type: str | None = None
    year: str | None = None
    browse_id: str = Field(alias="browseId")  # Album browse ID (MPREb_...)
    audio_playlist_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("audioPlaylistId", "playlistId"),
    )
    thumbnails: list[Thumbnail] = Field(default_factory=list)

    @property
    def url(self) -> str | None:
        """YouTube Music playlist URL for this release, if resolvable."""
        if not self.audio_playlist_id:
            return None
        return f"https://music.youtube.com/playlist?list={self.audio_playlist_id}"


class ArtistDiscography(YTMusicModel):
    """An artist's albums and singles, with playlist IDs resolved."""

    name: str
    channel_id: str
    thumbnails: list[Thumbnail] = Field(default_factory=list)
    albums: list[ArtistRelease] = Field(default_factory=list)
    singles: list[ArtistRelease] = Field(default_factory=list)
