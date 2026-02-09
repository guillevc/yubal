"""Subscription management endpoints."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from yubal import (
    APIError,
    AuthenticationRequiredError,
    PlaylistNotFoundError,
    PlaylistParseError,
    UnsupportedPlaylistError,
)

from yubal_api.api.deps import PlaylistInfoServiceDep, RepositoryDep, SchedulerDep
from yubal_api.db.subscription import Subscription, SubscriptionType
from yubal_api.schemas.subscriptions import (
    LibraryPlaylistListResponse,
    LibraryPlaylistResponse,
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
    repository: RepositoryDep,
    enabled: bool | None = None,
    type: SubscriptionType | None = None,
) -> SubscriptionListResponse:
    """List all subscriptions."""
    subscriptions = repository.list(enabled=enabled, type=type)
    return SubscriptionListResponse(
        items=[SubscriptionResponse.model_validate(s) for s in subscriptions]
    )


@router.get("/library-playlists", response_model=LibraryPlaylistListResponse)
def list_library_playlists(
    playlist_info_service: PlaylistInfoServiceDep,
) -> LibraryPlaylistListResponse:
    """List account library playlists."""
    try:
        playlists = playlist_info_service.list_library_playlists()
    except AuthenticationRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e
    except APIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e

    return LibraryPlaylistListResponse(
        items=[
            LibraryPlaylistResponse.model_validate(p, from_attributes=True)
            for p in playlists
        ]
    )


@router.post(
    "", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED
)
def create_subscription(
    data: SubscriptionCreate,
    repository: RepositoryDep,
    playlist_info_service: PlaylistInfoServiceDep,
) -> SubscriptionResponse:
    """Create a new subscription."""
    existing = repository.get_by_url(str(data.url))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Subscription with URL already exists: {existing.id}",
        )

    # Fetch metadata from YouTube Music
    try:
        metadata = playlist_info_service.get_playlist_metadata(str(data.url))
    except PlaylistNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except AuthenticationRequiredError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        ) from e
    except (PlaylistParseError, UnsupportedPlaylistError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    except APIError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        ) from e

    subscription = Subscription(
        type=SubscriptionType.PLAYLIST,
        url=str(data.url),
        name=metadata.title,
        thumbnail_url=metadata.thumbnail_url,
        enabled=True,
        max_items=data.max_items,
        created_at=datetime.now(UTC),
    )
    created = repository.create(subscription)
    return SubscriptionResponse.model_validate(created)


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: UUID,
    data: SubscriptionUpdate,
    repository: RepositoryDep,
) -> SubscriptionResponse:
    """Update a subscription."""
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        subscription = repository.get(subscription_id)
    else:
        subscription = repository.update(subscription_id, **updates)

    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )

    return SubscriptionResponse.model_validate(subscription)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    subscription_id: UUID,
    repository: RepositoryDep,
) -> None:
    """Delete a subscription."""
    if not repository.delete(subscription_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found",
        )


@router.post("/{subscription_id}/sync", response_model=SyncResponse)
async def sync_subscription(
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
