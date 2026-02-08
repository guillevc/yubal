"""Subscription business logic service."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from yubal import (
    APIError,
    AuthenticationRequiredError,
    PlaylistNotFoundError,
    PlaylistParseError,
    UnsupportedPlaylistError,
)

from yubal_api.api.exceptions import (
    MetadataFetchError,
    SubscriptionConflictError,
    SubscriptionNotFoundError,
)
from yubal_api.db.subscription import Subscription, SubscriptionType
from yubal_api.services.playlist_info import PlaylistInfoService
from yubal_api.services.protocols import SubscriptionRepo

logger = logging.getLogger(__name__)


class SubscriptionService:
    """Use-case layer for subscription operations.

    Encapsulates business logic for subscription CRUD, keeping route handlers
    thin (HTTP concerns only). PlaylistInfoService is injected as a concrete
    type (single implementation) — extract to a protocol if a second
    implementation is ever needed.
    """

    def __init__(
        self,
        repository: SubscriptionRepo,
        playlist_info: PlaylistInfoService,
    ) -> None:
        self._repository = repository
        self._playlist_info = playlist_info

    def list(
        self,
        *,
        enabled: bool | None = None,
        type: SubscriptionType | None = None,
    ) -> list[Subscription]:
        return self._repository.list(enabled=enabled, type=type)

    def get(self, subscription_id: UUID) -> Subscription:
        sub = self._repository.get(subscription_id)
        if sub is None:
            raise SubscriptionNotFoundError(subscription_id)
        return sub

    def create(self, url: str, max_items: int | None = None) -> Subscription:
        existing = self._repository.get_by_url(url)
        if existing is not None:
            raise SubscriptionConflictError(
                f"Subscription with URL already exists: {existing.id}",
                subscription_id=existing.id,
            )

        try:
            metadata = self._playlist_info.get_playlist_metadata(url)
        except (
            PlaylistNotFoundError,
            AuthenticationRequiredError,
            PlaylistParseError,
            UnsupportedPlaylistError,
            APIError,
        ):
            raise  # Known exceptions — propagate to exception handlers
        except Exception as e:
            logger.warning("Unexpected error fetching metadata for %s: %s", url, e)
            raise MetadataFetchError(str(e), upstream_error=type(e).__name__) from e

        subscription = Subscription(
            type=SubscriptionType.PLAYLIST,
            url=url,
            name=metadata.title,
            thumbnail_url=metadata.thumbnail_url,
            enabled=True,
            max_items=max_items,
            created_at=datetime.now(UTC),
        )
        return self._repository.create(subscription)

    def update(self, subscription_id: UUID, **kwargs: object) -> Subscription:
        if not kwargs:
            return self.get(subscription_id)
        sub = self._repository.update(subscription_id, **kwargs)
        if sub is None:
            raise SubscriptionNotFoundError(subscription_id)
        return sub

    def delete(self, subscription_id: UUID) -> None:
        if not self._repository.delete(subscription_id):
            raise SubscriptionNotFoundError(subscription_id)

    def update_metadata_by_url(
        self, url: str, name: str, thumbnail_url: str | None
    ) -> bool:
        """Update subscription metadata by URL (used by job executor after sync)."""
        sub = self._repository.get_by_url(url)
        if sub is None:
            return False
        self._repository.update(sub.id, name=name, thumbnail_url=thumbnail_url)
        return True
