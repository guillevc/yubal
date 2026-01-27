# Subscriptions API Design

Refactor the existing sync/playlists API to a cleaner subscriptions model with environment-based scheduler configuration.

## API Endpoints

### Subscriptions (`/api/subscriptions`)

```
GET    /api/subscriptions           List all (query: ?enabled=true&type=playlist)    200
POST   /api/subscriptions           Create subscription                              201 | 409 (duplicate url) | 422
GET    /api/subscriptions/{id}      Get one                                          200 | 404
PATCH  /api/subscriptions/{id}      Update (name, enabled)                           200 | 404 | 422
DELETE /api/subscriptions/{id}      Remove                                           204 | 404

POST   /api/subscriptions/sync      Sync all enabled                                 200 | 409 (queue full)
POST   /api/subscriptions/{id}/sync Sync one                                         200 | 404 | 409 (queue full)
```

> **Route ordering:** `/sync` routes must be registered before `/{id}` to avoid FastAPI capturing "sync" as an ID.

### Scheduler (`/api/scheduler`)

```
GET    /api/scheduler               Read-only status
```

## Environment Variables

```bash
YUBAL_SYNC_ENABLED=true          # scheduler on/off
YUBAL_SYNC_INTERVAL_MINUTES=60   # sync frequency (5-10080)
```

### Settings Schema

```python
# settings.py
sync_enabled: bool = Field(default=True, alias="YUBAL_SYNC_ENABLED")
sync_interval_minutes: int = Field(default=60, alias="YUBAL_SYNC_INTERVAL_MINUTES", ge=5, le=10080)
```

## Database

- **File:** `{YUBAL_CONFIG}/yubal.db` (renamed from `sync.db`)
- **Deleted tables:** `synced_playlist`, `sync_config`

### Subscription Model

```python
from enum import StrEnum
from datetime import datetime, UTC
from uuid import uuid4, UUID

class SubscriptionType(StrEnum):
    PLAYLIST = "playlist"
    # ARTIST = "artist"  # future

class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    type: SubscriptionType = Field(index=True)
    url: str = Field(unique=True, index=True)
    name: str = Field(max_length=200)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_synced_at: datetime | None = Field(default=None)
```

### Repository

```python
class SubscriptionRepository:
    def list(self, *, enabled: bool | None = None, type: SubscriptionType | None = None) -> list[Subscription]
    def get(self, id: UUID) -> Subscription | None
    def get_by_url(self, url: str) -> Subscription | None
    def create(self, subscription: Subscription) -> Subscription
    def update(self, subscription: Subscription) -> Subscription
    def delete(self, id: UUID) -> Subscription | None
    def count(self, *, enabled: bool | None = None, type: SubscriptionType | None = None) -> int
```

## Schemas

### Subscription Schemas

```python
class SubscriptionCreate(BaseModel):
    type: SubscriptionType = SubscriptionType.PLAYLIST
    url: HttpUrl
    name: str = Field(max_length=200)
    enabled: bool = True

class SubscriptionUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None

class SubscriptionResponse(BaseModel):
    id: UUID
    type: SubscriptionType
    url: str
    name: str
    enabled: bool
    created_at: datetime
    last_synced_at: datetime | None

class SubscriptionListResponse(BaseModel):
    items: list[SubscriptionResponse]

class SyncResponse(BaseModel):
    job_ids: list[str]  # Single item for one, multiple for bulk
```

### Scheduler Schemas

```python
class SubscriptionCounts(BaseModel):
    total: int
    enabled: int

class SchedulerStatus(BaseModel):
    running: bool
    enabled: bool
    interval_minutes: int
    next_run_at: datetime | None
    subscription_counts: SubscriptionCounts
```

## Implementation

### Files to Delete

- `api/routes/sync.py`
- `schemas/sync.py`
- `SyncedPlaylist`, `SyncConfig` from `db/models.py`

### Files to Create

- `api/routes/subscriptions.py` - CRUD + sync endpoints
- `api/routes/scheduler.py` - status endpoint
- `schemas/subscription.py` - request/response models
- `schemas/scheduler.py` - status response

### Files to Modify

- `db/engine.py` - rename `sync.db` → `yubal.db`
- `db/models.py` - add `Subscription`, `SubscriptionType`
- `db/repository.py` - replace `SyncRepository` with `SubscriptionRepository`
- `services/sync_service.py` - rename to `subscription_sync_service.py`
- `services/sync_scheduler.py` - rename to `scheduler.py`, read from env vars
- `settings.py` - add `YUBAL_SYNC_ENABLED`, `YUBAL_SYNC_INTERVAL_MINUTES`
- `api/app.py` - wire new routers and services
- `api/dependencies.py` - update dependency types

### Web Frontend

- Regenerate API client from OpenAPI
- Update pages using old `/api/sync/*` endpoints
