"""Subscription request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field

from yubal_api.db.subscription import SubscriptionType
from yubal_api.schemas.jobs import YouTubeMusicUrl
from yubal_api.schemas.types import UTCDateTime


class SubscriptionCreate(BaseModel):
    """Request to create a subscription."""

    url: YouTubeMusicUrl
    max_items: int | None = Field(default=None, ge=1, le=10000)


class SubscriptionUpdate(BaseModel):
    """Request to update a subscription."""

    enabled: bool | None = None
    max_items: int | None = Field(default=None, ge=1, le=10000)


class SubscriptionResponse(BaseModel):
    """Subscription response."""

    id: UUID
    type: SubscriptionType
    url: str = Field(json_schema_extra={"format": "uri"})
    name: str
    enabled: bool
    max_items: int | None
    thumbnail_url: str | None = Field(
        default=None,
        json_schema_extra={"format": "uri"},
    )
    created_at: UTCDateTime
    last_synced_at: UTCDateTime | None

    model_config = {"from_attributes": True}


class SubscriptionListResponse(BaseModel):
    """List of subscriptions response."""

    items: list[SubscriptionResponse]


class LibraryPlaylistResponse(BaseModel):
    """Library playlist response item."""

    playlist_id: str
    title: str
    name: str
    url: str = Field(json_schema_extra={"format": "uri"})
    thumbnail_url: str | None = Field(
        default=None,
        json_schema_extra={"format": "uri"},
    )
    track_count: int | None = Field(default=None, ge=0)


class LibraryPlaylistListResponse(BaseModel):
    """List of library playlists response."""

    items: list[LibraryPlaylistResponse]


class SyncResponse(BaseModel):
    """Response for sync operations."""

    job_ids: list[str]
