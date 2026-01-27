"""Subscription request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from yubal_api.db.models import SubscriptionType
from yubal_api.schemas.jobs import YouTubeMusicUrl


class SubscriptionCreate(BaseModel):
    """Request to create a subscription."""

    type: SubscriptionType = SubscriptionType.PLAYLIST
    url: YouTubeMusicUrl
    name: str = Field(min_length=1, max_length=200)
    enabled: bool = True


class SubscriptionUpdate(BaseModel):
    """Request to update a subscription."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    enabled: bool | None = None


class SubscriptionResponse(BaseModel):
    """Subscription response."""

    id: UUID
    type: SubscriptionType
    url: str
    name: str
    enabled: bool
    created_at: datetime
    last_synced_at: datetime | None

    model_config = {"from_attributes": True}


class SubscriptionListResponse(BaseModel):
    """List of subscriptions response."""

    items: list[SubscriptionResponse]


class SyncResponse(BaseModel):
    """Response for sync operations."""

    job_ids: list[str]
