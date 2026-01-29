"""Subscription request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from yubal_api.db.subscription import SubscriptionType
from yubal_api.schemas.jobs import YouTubeMusicUrl


class SubscriptionCreate(BaseModel):
    """Request to create a subscription."""

    url: YouTubeMusicUrl
    max_items: int | None = Field(default=None, ge=1, le=10000)


class SubscriptionUpdate(BaseModel):
    """Request to update a subscription."""

    enabled: bool | None = None


class SubscriptionResponse(BaseModel):
    """Subscription response."""

    id: UUID
    type: SubscriptionType
    url: str = Field(json_schema_extra={"format": "uri"})
    name: str
    enabled: bool
    max_items: int | None
    created_at: datetime
    last_synced_at: datetime | None

    model_config = {"from_attributes": True}


class SubscriptionListResponse(BaseModel):
    """List of subscriptions response."""

    items: list[SubscriptionResponse]


class SyncResponse(BaseModel):
    """Response for sync operations."""

    job_ids: list[str]
