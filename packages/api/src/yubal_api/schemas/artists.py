"""Artist API schemas."""

from pydantic import BaseModel, Field

from yubal_api.schemas.jobs import YouTubeMusicUrl


class ArtistSummary(BaseModel):
    """Artist search match."""

    channel_id: str = Field(description="YouTube Music artist channel ID")
    name: str
    thumbnail_url: str | None = None


class ArtistSearchResponse(BaseModel):
    """Response for artist search."""

    artists: list[ArtistSummary]


class ArtistRelease(BaseModel):
    """Album or single by an artist."""

    title: str
    type: str | None = Field(default=None, description="Album, Single, EP, ...")
    year: str | None = None
    url: str = Field(description="YouTube Music playlist URL for the release")
    thumbnail_url: str | None = None


class ArtistReleasesResponse(BaseModel):
    """An artist's albums and singles."""

    channel_id: str
    name: str
    thumbnail_url: str | None = None
    albums: list[ArtistRelease]
    singles: list[ArtistRelease]


class QueueArtistReleasesRequest(BaseModel):
    """Request to queue download jobs for artist releases."""

    urls: list[YouTubeMusicUrl] = Field(
        min_length=1,
        max_length=500,
        description="Release URLs (from GET /artists/{channel_id}/releases)",
    )


class QueueArtistReleasesResponse(BaseModel):
    """Result of queueing artist releases."""

    job_ids: list[str] = Field(description="IDs of the created jobs, in order")
    skipped: int = Field(
        default=0, description="Releases not queued because the queue was full"
    )
