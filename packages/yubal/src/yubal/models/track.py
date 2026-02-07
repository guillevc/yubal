"""Track and playlist metadata models."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from yubal.models.enums import ContentKind, SkipReason, VideoType


class UnavailableTrack(BaseModel):
    """Track unavailable at source with metadata for display.

    Used to store information about tracks that couldn't be extracted
    due to missing video ID or region restrictions.

    Attributes:
        title: Track title (may be None if unavailable).
        artists: List of artist names.
        album: Album name (may be None if unavailable).
        reason: Why the track is unavailable.
    """

    model_config = ConfigDict(frozen=True)

    title: str | None = None
    artists: list[str] = Field(default_factory=list)
    album: str | None = None
    reason: SkipReason

    @property
    def artist_display(self) -> str:
        """Formatted artist string for display."""
        return ", ".join(self.artists) if self.artists else "Unknown Artist"


class TrackMetadata(BaseModel):
    """Metadata for a single track."""

    model_config = ConfigDict(frozen=True)

    omv_video_id: str | None = None
    atv_video_id: str | None = None
    title: str
    artists: list[str]
    album: str
    album_artists: list[str]
    track_number: int | None = None
    total_tracks: int | None = None
    year: str | None = None
    cover_url: str | None = None
    video_type: VideoType | None = None
    duration_seconds: int | None = None
    unmatched: bool = False

    @field_validator("title", "album")
    @classmethod
    def non_empty_string(cls, v: str) -> str:
        """Validate that title and album are non-empty strings."""
        if not v or not v.strip():
            raise ValueError("must not be empty")
        return v

    @field_validator("artists", "album_artists")
    @classmethod
    def non_empty_list(cls, v: list[str]) -> list[str]:
        """Validate that artists lists have at least one non-empty entry."""
        if not v:
            raise ValueError("must have at least one entry")
        if not any(a.strip() for a in v):
            raise ValueError("must have at least one non-empty entry")
        return v

    @property
    def artist(self) -> str:
        """Joined artists for display and Jellyfin parsing.

        Uses ' / ' delimiter which Jellyfin parses to link artists.
        """
        return " / ".join(self.artists)

    @property
    def album_artist(self) -> str:
        """Joined album artists for display and Jellyfin parsing."""
        return " / ".join(self.album_artists)

    @property
    def primary_album_artist(self) -> str:
        """First album artist for path construction."""
        return self.album_artists[0] if self.album_artists else "Unknown Artist"


class PlaylistInfo(BaseModel):
    """Information about a playlist.

    Contains metadata about the playlist itself, separate from track data.

    Attributes:
        playlist_id: The YouTube Music playlist ID.
        title: The playlist title/name.
        cover_url: URL to the playlist cover image.
        kind: Whether this is an album or playlist.
        author: Channel/creator name (for playlists).
        unavailable_tracks: Tracks that couldn't be extracted with reasons.
    """

    model_config = ConfigDict(frozen=True)

    playlist_id: str
    title: str | None = None
    cover_url: str | None = None
    kind: ContentKind = ContentKind.PLAYLIST
    author: str | None = None
    unavailable_tracks: list[UnavailableTrack] = Field(default_factory=list)
