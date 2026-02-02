"""Tests for subscription repository."""

from uuid import uuid4

from yubal_api.db.repository import SubscriptionRepository
from yubal_api.db.subscription import Subscription, SubscriptionType


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

        found = repository.get_by_url(
            "https://music.youtube.com/playlist?list=PLunique"
        )
        assert found is not None
        assert found.name == "Unique Playlist"

        not_found = repository.get_by_url("https://example.com/nonexistent")
        assert not_found is None

    def test_list_filters(self, repository: SubscriptionRepository) -> None:
        """Should filter subscriptions by enabled and type."""
        repository.create(
            Subscription(
                type=SubscriptionType.PLAYLIST,
                url="https://music.youtube.com/playlist?list=PL1",
                name="Enabled Playlist",
                enabled=True,
            )
        )
        repository.create(
            Subscription(
                type=SubscriptionType.PLAYLIST,
                url="https://music.youtube.com/playlist?list=PL2",
                name="Disabled Playlist",
                enabled=False,
            )
        )

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

        updated = repository.update(created.id, name="Updated Name", enabled=False)

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.enabled is False

    def test_delete(self, repository: SubscriptionRepository) -> None:
        """Should delete subscription and return True, or False if not found."""
        sub = Subscription(
            type=SubscriptionType.PLAYLIST,
            url="https://music.youtube.com/playlist?list=PLdelete",
            name="To Delete",
        )
        created = repository.create(sub)

        assert repository.delete(created.id) is True
        assert repository.get(created.id) is None
        assert repository.delete(uuid4()) is False

    def test_count(self, repository: SubscriptionRepository) -> None:
        """Should count subscriptions with filters."""
        repository.create(
            Subscription(
                type=SubscriptionType.PLAYLIST,
                url="https://music.youtube.com/playlist?list=PL1",
                name="P1",
                enabled=True,
            )
        )
        repository.create(
            Subscription(
                type=SubscriptionType.PLAYLIST,
                url="https://music.youtube.com/playlist?list=PL2",
                name="P2",
                enabled=False,
            )
        )

        assert repository.count() == 2
        assert repository.count(enabled=True) == 1
        assert repository.count(enabled=False) == 1
