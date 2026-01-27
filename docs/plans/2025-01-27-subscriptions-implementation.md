# Subscriptions API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor sync/playlists API to subscriptions model with environment-based scheduler configuration.

**Architecture:** Replace `SyncedPlaylist`/`SyncConfig` models with a single `Subscription` model. Move scheduler config to environment variables. Rename database from `sync.db` to `yubal.db`.

**Tech Stack:** FastAPI, SQLModel, Pydantic, pytest

---

## Task 1: Add Settings for Scheduler

**Files:**
- Modify: `packages/api/yubal_api/settings.py`
- Test: `packages/api/tests/test_settings.py`

**Step 1: Add scheduler settings to Settings class**

In `packages/api/yubal_api/settings.py`, add after `cors_origins` field:

```python
    # Scheduler settings
    sync_enabled: bool = Field(default=True, alias="YUBAL_SYNC_ENABLED")
    sync_interval_minutes: int = Field(
        default=60, alias="YUBAL_SYNC_INTERVAL_MINUTES", ge=5, le=10080
    )
```

**Step 2: Run tests to verify settings work**

Run: `just test`
Expected: PASS (existing tests still pass)

**Step 3: Commit**

```bash
git add packages/api/yubal_api/settings.py
git commit -m "feat(api): add scheduler env var settings"
```

---

## Task 2: Create Subscription Model

**Files:**
- Modify: `packages/api/yubal_api/db/models.py`

**Step 1: Add SubscriptionType enum and Subscription model**

Replace the entire `models.py` with:

```python
"""Database models."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class SubscriptionType(StrEnum):
    """Type of content subscription."""

    PLAYLIST = "playlist"
    # ARTIST = "artist"  # future


class Subscription(SQLModel, table=True):
    """A subscription to sync content from YouTube Music."""

    __tablename__ = "subscriptions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    type: SubscriptionType = Field(index=True)
    url: str = Field(unique=True, index=True)
    name: str = Field(max_length=200)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_synced_at: datetime | None = Field(default=None)
```

**Step 2: Verify no syntax errors**

Run: `just typecheck`
Expected: PASS (may have errors in dependent files, that's expected)

**Step 3: Commit**

```bash
git add packages/api/yubal_api/db/models.py
git commit -m "feat(api): add Subscription model, remove SyncedPlaylist/SyncConfig"
```

---

## Task 3: Update Database Engine

**Files:**
- Modify: `packages/api/yubal_api/db/engine.py`

**Step 1: Rename database file from sync.db to yubal.db**

Change the `DB_FILE` constant:

```python
DB_FILE = "yubal.db"
```

**Step 2: Commit**

```bash
git add packages/api/yubal_api/db/engine.py
git commit -m "refactor(api): rename database sync.db to yubal.db"
```

---

## Task 4: Create Subscription Repository

**Files:**
- Modify: `packages/api/yubal_api/db/repository.py`

**Step 1: Replace SyncRepository with SubscriptionRepository**

Replace the entire `repository.py` with:

```python
"""Database repository for subscriptions."""

from uuid import UUID

from sqlmodel import Session, col, create_engine, select

from yubal_api.db.models import Subscription, SubscriptionType


class SubscriptionRepository:
    """Repository for subscription database operations."""

    def __init__(self, engine: create_engine) -> None:
        """Initialize repository with database engine."""
        self._engine = engine

    def list(
        self,
        *,
        enabled: bool | None = None,
        type: SubscriptionType | None = None,
    ) -> list[Subscription]:
        """List subscriptions with optional filters."""
        with Session(self._engine) as session:
            stmt = select(Subscription).order_by(col(Subscription.created_at).desc())
            if enabled is not None:
                stmt = stmt.where(Subscription.enabled == enabled)
            if type is not None:
                stmt = stmt.where(Subscription.type == type)
            return list(session.exec(stmt).all())

    def get(self, id: UUID) -> Subscription | None:
        """Get subscription by ID."""
        with Session(self._engine) as session:
            return session.get(Subscription, id)

    def get_by_url(self, url: str) -> Subscription | None:
        """Get subscription by URL."""
        with Session(self._engine) as session:
            stmt = select(Subscription).where(Subscription.url == url)
            return session.exec(stmt).first()

    def create(self, subscription: Subscription) -> Subscription:
        """Create a new subscription."""
        with Session(self._engine) as session:
            session.add(subscription)
            session.commit()
            session.refresh(subscription)
            return subscription

    def update(self, subscription: Subscription, **kwargs: object) -> Subscription:
        """Update subscription fields."""
        with Session(self._engine) as session:
            # Re-fetch within this session
            db_subscription = session.get(Subscription, subscription.id)
            if db_subscription is None:
                msg = f"Subscription {subscription.id} not found"
                raise ValueError(msg)
            for key, value in kwargs.items():
                setattr(db_subscription, key, value)
            session.commit()
            session.refresh(db_subscription)
            return db_subscription

    def delete(self, id: UUID) -> Subscription | None:
        """Delete subscription by ID. Returns deleted subscription or None."""
        with Session(self._engine) as session:
            subscription = session.get(Subscription, id)
            if subscription is None:
                return None
            session.delete(subscription)
            session.commit()
            return subscription

    def count(
        self,
        *,
        enabled: bool | None = None,
        type: SubscriptionType | None = None,
    ) -> int:
        """Count subscriptions with optional filters."""
        from sqlmodel import func

        with Session(self._engine) as session:
            stmt = select(func.count()).select_from(Subscription)
            if enabled is not None:
                stmt = stmt.where(Subscription.enabled == enabled)
            if type is not None:
                stmt = stmt.where(Subscription.type == type)
            return session.exec(stmt).one()
```

**Step 2: Commit**

```bash
git add packages/api/yubal_api/db/repository.py
git commit -m "refactor(api): replace SyncRepository with SubscriptionRepository"
```

---

## Task 5: Create Subscription Schemas

**Files:**
- Create: `packages/api/yubal_api/schemas/subscription.py`
- Delete: `packages/api/yubal_api/schemas/sync.py`

**Step 1: Create subscription schemas**

Create `packages/api/yubal_api/schemas/subscription.py`:

```python
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
```

**Step 2: Delete old sync schemas**

```bash
rm packages/api/yubal_api/schemas/sync.py
```

**Step 3: Update schemas __init__.py if it exists**

Check if `packages/api/yubal_api/schemas/__init__.py` exports sync schemas and update accordingly.

**Step 4: Commit**

```bash
git add packages/api/yubal_api/schemas/
git commit -m "feat(api): add subscription schemas, remove sync schemas"
```

---

## Task 6: Create Scheduler Schemas

**Files:**
- Create: `packages/api/yubal_api/schemas/scheduler.py`

**Step 1: Create scheduler schemas**

Create `packages/api/yubal_api/schemas/scheduler.py`:

```python
"""Scheduler status schemas."""

from datetime import datetime

from pydantic import BaseModel


class SubscriptionCounts(BaseModel):
    """Subscription count statistics."""

    total: int
    enabled: int


class SchedulerStatus(BaseModel):
    """Scheduler status response."""

    running: bool
    enabled: bool
    interval_minutes: int
    next_run_at: datetime | None
    subscription_counts: SubscriptionCounts
```

**Step 2: Commit**

```bash
git add packages/api/yubal_api/schemas/scheduler.py
git commit -m "feat(api): add scheduler status schema"
```

---

## Task 7: Refactor Scheduler Service

**Files:**
- Rename: `packages/api/yubal_api/services/sync_scheduler.py` → `packages/api/yubal_api/services/scheduler.py`

**Step 1: Rename and refactor scheduler**

Rename file and update to use settings instead of database config:

```bash
mv packages/api/yubal_api/services/sync_scheduler.py packages/api/yubal_api/services/scheduler.py
```

Then replace contents with:

```python
"""Background scheduler for periodic subscription syncing."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from yubal_api.db.models import Subscription
from yubal_api.db.repository import SubscriptionRepository
from yubal_api.services.job_store import JobStore
from yubal_api.settings import Settings

logger = logging.getLogger(__name__)


class Scheduler:
    """Background scheduler that syncs enabled subscriptions periodically."""

    def __init__(
        self,
        repository: SubscriptionRepository,
        job_store: JobStore,
        settings: Settings,
    ) -> None:
        """Initialize scheduler."""
        self._repository = repository
        self._job_store = job_store
        self._settings = settings
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._next_run_at: datetime | None = None

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._task is not None and not self._task.done()

    @property
    def enabled(self) -> bool:
        """Check if scheduler is enabled (from settings)."""
        return self._settings.sync_enabled

    @property
    def interval_minutes(self) -> int:
        """Get sync interval in minutes (from settings)."""
        return self._settings.sync_interval_minutes

    @property
    def next_run_at(self) -> datetime | None:
        """Get next scheduled run time."""
        return self._next_run_at

    def start(self) -> None:
        """Start the scheduler background task."""
        if self._task is not None:
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler background task."""
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None
        self._next_run_at = None
        logger.info("Scheduler stopped")

    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            interval = self._settings.sync_interval_minutes * 60
            self._next_run_at = datetime.now(UTC) + timedelta(seconds=interval)

            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=interval,
                )
                break  # Stop event was set
            except asyncio.TimeoutError:
                pass  # Timeout expired, time to sync

            if self._settings.sync_enabled:
                await self._sync_all_enabled()

    def _create_jobs_for_subscriptions(
        self, subscriptions: list[Subscription]
    ) -> list[str]:
        """Create sync jobs for given subscriptions."""
        job_ids: list[str] = []
        for subscription in subscriptions:
            try:
                job = self._job_store.create(subscription.url)
                job_ids.append(job.id)
                self._repository.update(
                    subscription,
                    last_synced_at=datetime.now(UTC),
                )
                logger.info(
                    "Created sync job %s for subscription %s",
                    job.id[:8],
                    subscription.name,
                )
            except Exception:
                logger.exception(
                    "Failed to create job for subscription %s",
                    subscription.name,
                )
        return job_ids

    async def _sync_all_enabled(self) -> list[str]:
        """Sync all enabled subscriptions (async wrapper)."""
        return self._create_jobs_for_subscriptions(self._repository.list(enabled=True))

    def sync_subscription(self, subscription_id: str) -> str | None:
        """Create sync job for a single subscription. Returns job_id or None."""
        from uuid import UUID

        subscription = self._repository.get(UUID(subscription_id))
        if subscription is None:
            return None

        job_ids = self._create_jobs_for_subscriptions([subscription])
        return job_ids[0] if job_ids else None

    def sync_all(self) -> list[str]:
        """Create sync jobs for all enabled subscriptions. Returns job_ids."""
        return self._create_jobs_for_subscriptions(self._repository.list(enabled=True))
```

**Step 2: Delete old sync_scheduler.py if not already renamed**

```bash
rm -f packages/api/yubal_api/services/sync_scheduler.py
```

**Step 3: Commit**

```bash
git add packages/api/yubal_api/services/
git commit -m "refactor(api): rename SyncScheduler to Scheduler, use env settings"
```

---

## Task 8: Create Subscriptions Router

**Files:**
- Create: `packages/api/yubal_api/api/routes/subscriptions.py`
- Delete: `packages/api/yubal_api/api/routes/sync.py`

**Step 1: Create subscriptions router**

Create `packages/api/yubal_api/api/routes/subscriptions.py`:

```python
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


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    data: SubscriptionCreate,
    repository: RepositoryDep,
) -> SubscriptionResponse:
    """Create a new subscription."""
    # Check for duplicate URL
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
```

**Step 2: Delete old sync router**

```bash
rm packages/api/yubal_api/api/routes/sync.py
```

**Step 3: Commit**

```bash
git add packages/api/yubal_api/api/routes/
git commit -m "feat(api): add subscriptions router, remove sync router"
```

---

## Task 9: Create Scheduler Router

**Files:**
- Create: `packages/api/yubal_api/api/routes/scheduler.py`

**Step 1: Create scheduler router**

Create `packages/api/yubal_api/api/routes/scheduler.py`:

```python
"""Scheduler status endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends
from starlette.requests import Request

from yubal_api.db.repository import SubscriptionRepository
from yubal_api.schemas.scheduler import SchedulerStatus, SubscriptionCounts
from yubal_api.services.scheduler import Scheduler

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


def get_repository(request: Request) -> SubscriptionRepository:
    """Get subscription repository from app state."""
    return request.app.state.services.repository


def get_scheduler(request: Request) -> Scheduler:
    """Get scheduler from app state."""
    return request.app.state.services.scheduler


RepositoryDep = Annotated[SubscriptionRepository, Depends(get_repository)]
SchedulerDep = Annotated[Scheduler, Depends(get_scheduler)]


@router.get("", response_model=SchedulerStatus)
def get_scheduler_status(
    repository: RepositoryDep,
    scheduler: SchedulerDep,
) -> SchedulerStatus:
    """Get scheduler status (read-only)."""
    return SchedulerStatus(
        running=scheduler.is_running,
        enabled=scheduler.enabled,
        interval_minutes=scheduler.interval_minutes,
        next_run_at=scheduler.next_run_at,
        subscription_counts=SubscriptionCounts(
            total=repository.count(),
            enabled=repository.count(enabled=True),
        ),
    )
```

**Step 2: Commit**

```bash
git add packages/api/yubal_api/api/routes/scheduler.py
git commit -m "feat(api): add scheduler status endpoint"
```

---

## Task 10: Update Dependencies

**Files:**
- Modify: `packages/api/yubal_api/api/dependencies.py`

**Step 1: Update dependencies to use new types**

Update imports and type aliases in `dependencies.py`. Replace references to `SyncRepository` with `SubscriptionRepository` and `SyncScheduler` with `Scheduler`.

Find and replace:
- `SyncRepository` → `SubscriptionRepository`
- `SyncScheduler` → `Scheduler`
- `sync_scheduler` → `scheduler`
- `sync_repository` → `repository`

**Step 2: Commit**

```bash
git add packages/api/yubal_api/api/dependencies.py
git commit -m "refactor(api): update dependencies for subscriptions"
```

---

## Task 11: Update App Factory

**Files:**
- Modify: `packages/api/yubal_api/api/app.py`

**Step 1: Update imports**

Replace:
```python
from yubal_api.api.routes import cookies, health, jobs, logs, sync
from yubal_api.services.sync_scheduler import SyncScheduler
```

With:
```python
from yubal_api.api.routes import cookies, health, jobs, logs, scheduler, subscriptions
from yubal_api.services.scheduler import Scheduler
```

**Step 2: Update create_services function**

Replace `SyncScheduler` instantiation with `Scheduler`, passing settings:

```python
scheduler = Scheduler(
    repository=repository,
    job_store=job_store,
    settings=settings,
)
```

**Step 3: Update Services dataclass**

Replace `sync_scheduler` field with `scheduler` and `sync_repository` with `repository`.

**Step 4: Update router registration**

Replace:
```python
router.include_router(sync.router)
```

With:
```python
router.include_router(subscriptions.router)
router.include_router(scheduler.router)
```

**Step 5: Update lifespan handler**

Replace references to `sync_scheduler` with `scheduler`.

**Step 6: Commit**

```bash
git add packages/api/yubal_api/api/app.py
git commit -m "refactor(api): wire subscriptions and scheduler in app factory"
```

---

## Task 12: Update Web Frontend API Client

**Files:**
- Run: `just gen-api`
- Modify: Web pages using old sync API

**Step 1: Regenerate TypeScript types**

```bash
just gen-api
```

**Step 2: Update web pages**

Search for usages of old `/api/sync` endpoints in the web package and update to use `/api/subscriptions` and `/api/scheduler`.

**Step 3: Commit**

```bash
git add packages/web/
git commit -m "feat(web): update to subscriptions API"
```

---

## Task 13: Update Tests

**Files:**
- Delete: Any `test_sync_*.py` files in `packages/api/tests/`
- Create: `packages/api/tests/test_repository.py`

**Step 1: Create repository tests**

Create `packages/api/tests/test_repository.py`:

```python
"""Tests for subscription repository."""

import pytest
from sqlmodel import Session, SQLModel, create_engine

from yubal_api.db.models import Subscription, SubscriptionType
from yubal_api.db.repository import SubscriptionRepository


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for tests."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def repository(engine):
    """Create repository with test engine."""
    return SubscriptionRepository(engine)


class TestSubscriptionRepository:
    """Tests for SubscriptionRepository."""

    def test_create_and_get(self, repository: SubscriptionRepository) -> None:
        """Should create and retrieve a subscription."""
        sub = Subscription(
            type=SubscriptionType.PLAYLIST,
            url="https://music.youtube.com/playlist?list=PLtest",
            name="Test Playlist",
        )
        created = repository.create(sub)

        assert created.id is not None
        assert created.name == "Test Playlist"

        fetched = repository.get(created.id)
        assert fetched is not None
        assert fetched.url == sub.url

    def test_get_by_url(self, repository: SubscriptionRepository) -> None:
        """Should find subscription by URL."""
        sub = Subscription(
            type=SubscriptionType.PLAYLIST,
            url="https://music.youtube.com/playlist?list=PLunique",
            name="Unique Playlist",
        )
        repository.create(sub)

        found = repository.get_by_url("https://music.youtube.com/playlist?list=PLunique")
        assert found is not None
        assert found.name == "Unique Playlist"

        not_found = repository.get_by_url("https://example.com/nonexistent")
        assert not_found is None

    def test_list_filters(self, repository: SubscriptionRepository) -> None:
        """Should filter subscriptions by enabled and type."""
        repository.create(Subscription(
            type=SubscriptionType.PLAYLIST,
            url="https://music.youtube.com/playlist?list=PL1",
            name="Enabled Playlist",
            enabled=True,
        ))
        repository.create(Subscription(
            type=SubscriptionType.PLAYLIST,
            url="https://music.youtube.com/playlist?list=PL2",
            name="Disabled Playlist",
            enabled=False,
        ))

        all_subs = repository.list()
        assert len(all_subs) == 2

        enabled = repository.list(enabled=True)
        assert len(enabled) == 1
        assert enabled[0].name == "Enabled Playlist"

        disabled = repository.list(enabled=False)
        assert len(disabled) == 1
        assert disabled[0].name == "Disabled Playlist"

    def test_update(self, repository: SubscriptionRepository) -> None:
        """Should update subscription fields."""
        sub = Subscription(
            type=SubscriptionType.PLAYLIST,
            url="https://music.youtube.com/playlist?list=PLupdate",
            name="Original Name",
            enabled=True,
        )
        created = repository.create(sub)

        updated = repository.update(created, name="Updated Name", enabled=False)

        assert updated.name == "Updated Name"
        assert updated.enabled is False

    def test_delete(self, repository: SubscriptionRepository) -> None:
        """Should delete subscription and return it."""
        sub = Subscription(
            type=SubscriptionType.PLAYLIST,
            url="https://music.youtube.com/playlist?list=PLdelete",
            name="To Delete",
        )
        created = repository.create(sub)

        deleted = repository.delete(created.id)
        assert deleted is not None
        assert deleted.name == "To Delete"

        # Should be gone
        assert repository.get(created.id) is None

        # Delete non-existent returns None
        from uuid import uuid4
        assert repository.delete(uuid4()) is None

    def test_count(self, repository: SubscriptionRepository) -> None:
        """Should count subscriptions with filters."""
        repository.create(Subscription(
            type=SubscriptionType.PLAYLIST,
            url="https://music.youtube.com/playlist?list=PL1",
            name="P1",
            enabled=True,
        ))
        repository.create(Subscription(
            type=SubscriptionType.PLAYLIST,
            url="https://music.youtube.com/playlist?list=PL2",
            name="P2",
            enabled=False,
        ))

        assert repository.count() == 2
        assert repository.count(enabled=True) == 1
        assert repository.count(enabled=False) == 1
```

**Step 2: Run tests to verify**

Run: `just test`
Expected: PASS

**Step 3: Commit**

```bash
git add packages/api/tests/
git commit -m "test(api): add subscription repository tests"
```

---

## Task 14: Run Full Check

**Step 1: Format and lint**

```bash
just format
just lint-fix
```

**Step 2: Run all checks**

```bash
just check
```

**Step 3: Fix any remaining issues**

Address typecheck errors, test failures, or lint issues.

**Step 4: Final commit**

```bash
git add -A
git commit -m "chore: fix lint and typecheck issues"
```

---

## Task 15: Manual Testing

**Step 1: Start dev server**

```bash
just dev
```

**Step 2: Test endpoints manually**

```bash
# Create subscription
curl -X POST http://localhost:8000/api/subscriptions \
  -H "Content-Type: application/json" \
  -d '{"url": "https://music.youtube.com/playlist?list=PLtest", "name": "Test Playlist"}'

# List subscriptions
curl http://localhost:8000/api/subscriptions

# Get scheduler status
curl http://localhost:8000/api/scheduler

# Sync single subscription (use ID from create response)
curl -X POST http://localhost:8000/api/subscriptions/{id}/sync

# Sync all
curl -X POST http://localhost:8000/api/subscriptions/sync
```

**Step 3: Verify web UI works**

Open http://localhost:5173 and test subscription management.
