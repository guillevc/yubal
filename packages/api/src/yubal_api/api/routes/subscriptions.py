"""Subscription management endpoints."""

from uuid import UUID

from fastapi import APIRouter, status

from yubal_api.api.deps import SchedulerDep, SubscriptionServiceDep
from yubal_api.api.exceptions import QueueFullError
from yubal_api.db.subscription import SubscriptionType
from yubal_api.schemas.subscriptions import (
    SubscriptionCreate,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
    SyncResponse,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


# =============================================================================
# Sync routes MUST be registered BEFORE /{subscription_id} routes
# FastAPI matches routes in order - "sync" would be captured as a UUID otherwise
# =============================================================================


@router.post("/sync", response_model=SyncResponse)
async def sync_all_subscriptions(
    scheduler: SchedulerDep,
) -> SyncResponse:
    """Sync all enabled subscriptions."""
    job_ids = scheduler.sync_all()
    return SyncResponse(job_ids=job_ids)


# =============================================================================
# CRUD routes
# =============================================================================


@router.get("", response_model=SubscriptionListResponse)
def list_subscriptions(
    service: SubscriptionServiceDep,
    enabled: bool | None = None,
    type: SubscriptionType | None = None,
) -> SubscriptionListResponse:
    """List all subscriptions."""
    subscriptions = service.list(enabled=enabled, type=type)
    return SubscriptionListResponse(
        items=[SubscriptionResponse.model_validate(s) for s in subscriptions]
    )


@router.post(
    "", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
def create_subscription(
    data: SubscriptionCreate,
    service: SubscriptionServiceDep,
) -> SubscriptionResponse:
    """Create a new subscription."""
    created = service.create(str(data.url), data.max_items)
    return SubscriptionResponse.model_validate(created)


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: UUID,
    data: SubscriptionUpdate,
    service: SubscriptionServiceDep,
) -> SubscriptionResponse:
    """Update a subscription."""
    updates = data.model_dump(exclude_unset=True)
    subscription = service.update(subscription_id, **updates)
    return SubscriptionResponse.model_validate(subscription)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    subscription_id: UUID,
    service: SubscriptionServiceDep,
) -> None:
    """Delete a subscription."""
    service.delete(subscription_id)


@router.post("/{subscription_id}/sync", response_model=SyncResponse)
async def sync_subscription(
    subscription_id: UUID,
    service: SubscriptionServiceDep,
    scheduler: SchedulerDep,
) -> SyncResponse:
    """Sync a single subscription."""
    service.get(
        subscription_id
    )  # Validates existence, raises SubscriptionNotFoundError
    job_id = scheduler.sync_subscription(str(subscription_id))
    if job_id is None:
        raise QueueFullError()
    return SyncResponse(job_ids=[job_id])
