"""Subscription management endpoints."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.requests import Request

from yubal_api.db.models import Subscription, SubscriptionType
from yubal_api.db.repository import SubscriptionRepository
from yubal_api.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionListResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
    SyncResponse,
)
from yubal_api.services.scheduler import Scheduler

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def get_repository(request: Request) -> SubscriptionRepository:
    """Get subscription repository from app state."""
    return request.app.state.services.repository


def get_scheduler(request: Request) -> Scheduler:
    """Get scheduler from app state."""
    return request.app.state.services.scheduler


RepositoryDep = Annotated[SubscriptionRepository, Depends(get_repository)]
SchedulerDep = Annotated[Scheduler, Depends(get_scheduler)]


# =============================================================================
# Sync routes MUST be registered BEFORE /{subscription_id} routes
# FastAPI matches routes in order - "sync" would be captured as a UUID otherwise
# =============================================================================


@router.post("/sync", response_model=SyncResponse)
def sync_all_subscriptions(
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
    repository: RepositoryDep,
    enabled: bool | None = None,
    type: SubscriptionType | None = None,
) -> SubscriptionListResponse:
    """List all subscriptions."""
    subscriptions = repository.list(enabled=enabled, type=type)
    return SubscriptionListResponse(
        items=[SubscriptionResponse.model_validate(s) for s in subscriptions]
    )


@router.post(
    "", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
def create_subscription(
    data: SubscriptionCreate,
    repository: RepositoryDep,
) -> SubscriptionResponse:
    """Create a new subscription."""
    existing = repository.get_by_url(str(data.url))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subscription with URL already exists: {existing.id}",
        )

    subscription = Subscription(
        type=data.type,
        url=str(data.url),
        name=data.name,
        enabled=data.enabled,
        created_at=datetime.now(UTC),
    )
    created = repository.create(subscription)
    return SubscriptionResponse.model_validate(created)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: UUID,
    repository: RepositoryDep,
) -> SubscriptionResponse:
    """Get a subscription by ID."""
    subscription = repository.get(subscription_id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )
    return SubscriptionResponse.model_validate(subscription)


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: UUID,
    data: SubscriptionUpdate,
    repository: RepositoryDep,
) -> SubscriptionResponse:
    """Update a subscription."""
    subscription = repository.get(subscription_id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    updates = data.model_dump(exclude_unset=True)
    if updates:
        subscription = repository.update(subscription, **updates)

    return SubscriptionResponse.model_validate(subscription)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    subscription_id: UUID,
    repository: RepositoryDep,
) -> None:
    """Delete a subscription."""
    deleted = repository.delete(subscription_id)
    if deleted is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )


@router.post("/{subscription_id}/sync", response_model=SyncResponse)
def sync_subscription(
    subscription_id: UUID,
    repository: RepositoryDep,
    scheduler: SchedulerDep,
) -> SyncResponse:
    """Sync a single subscription."""
    subscription = repository.get(subscription_id)
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    job_id = scheduler.sync_subscription(str(subscription_id))
    if job_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to create sync job (queue may be full)",
        )

    return SyncResponse(job_ids=[job_id])
