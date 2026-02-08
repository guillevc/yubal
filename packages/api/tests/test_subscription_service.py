"""Tests for SubscriptionService."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from yubal import APIError, PlaylistNotFoundError
from yubal_api.api.exceptions import (
    MetadataFetchError,
    SubscriptionConflictError,
    SubscriptionNotFoundError,
)
from yubal_api.db.subscription import Subscription, SubscriptionType
from yubal_api.services.playlist_info import PlaylistInfoService, PlaylistMetadata
from yubal_api.services.subscription_service import SubscriptionService


@pytest.fixture
def mock_repo() -> MagicMock:
    """Create a mock SubscriptionRepo."""
    return MagicMock()


@pytest.fixture
def mock_playlist_info() -> MagicMock:
    """Create a mock PlaylistInfoService."""
    return MagicMock(spec=PlaylistInfoService)


@pytest.fixture
def service(mock_repo: MagicMock, mock_playlist_info: MagicMock) -> SubscriptionService:
    """Create a SubscriptionService with mocked dependencies."""
    return SubscriptionService(repository=mock_repo, playlist_info=mock_playlist_info)


@pytest.fixture
def sample_subscription() -> Subscription:
    """Create a sample subscription for tests."""
    return Subscription(
        id=uuid4(),
        type=SubscriptionType.PLAYLIST,
        url="https://music.youtube.com/playlist?list=PLtest",
        name="Test Playlist",
        enabled=True,
        created_at=datetime.now(UTC),
    )


class TestGet:
    def test_get_found(
        self,
        service: SubscriptionService,
        mock_repo: MagicMock,
        sample_subscription: Subscription,
    ) -> None:
        mock_repo.get.return_value = sample_subscription
        result = service.get(sample_subscription.id)
        assert result == sample_subscription
        mock_repo.get.assert_called_once_with(sample_subscription.id)

    def test_get_not_found(
        self, service: SubscriptionService, mock_repo: MagicMock
    ) -> None:
        mock_repo.get.return_value = None
        sub_id = uuid4()
        with pytest.raises(SubscriptionNotFoundError) as exc_info:
            service.get(sub_id)
        assert exc_info.value.subscription_id == sub_id


class TestCreate:
    def test_create_success(
        self,
        service: SubscriptionService,
        mock_repo: MagicMock,
        mock_playlist_info: MagicMock,
    ) -> None:
        mock_repo.get_by_url.return_value = None
        mock_playlist_info.get_playlist_metadata.return_value = PlaylistMetadata(
            title="My Playlist", thumbnail_url="https://example.com/thumb.jpg"
        )
        created_sub = Subscription(
            id=uuid4(),
            type=SubscriptionType.PLAYLIST,
            url="https://music.youtube.com/playlist?list=PLnew",
            name="My Playlist",
            enabled=True,
            created_at=datetime.now(UTC),
        )
        mock_repo.create.return_value = created_sub

        result = service.create("https://music.youtube.com/playlist?list=PLnew")

        assert result == created_sub
        mock_repo.get_by_url.assert_called_once()
        mock_playlist_info.get_playlist_metadata.assert_called_once()
        mock_repo.create.assert_called_once()

    def test_create_conflict(
        self,
        service: SubscriptionService,
        mock_repo: MagicMock,
        sample_subscription: Subscription,
    ) -> None:
        mock_repo.get_by_url.return_value = sample_subscription

        with pytest.raises(SubscriptionConflictError) as exc_info:
            service.create(sample_subscription.url)
        assert exc_info.value.subscription_id == sample_subscription.id

    def test_create_known_exception_propagates(
        self,
        service: SubscriptionService,
        mock_repo: MagicMock,
        mock_playlist_info: MagicMock,
    ) -> None:
        mock_repo.get_by_url.return_value = None
        mock_playlist_info.get_playlist_metadata.side_effect = PlaylistNotFoundError(
            "PL123"
        )

        with pytest.raises(PlaylistNotFoundError):
            service.create("https://music.youtube.com/playlist?list=PLbad")

    def test_create_api_error_propagates(
        self,
        service: SubscriptionService,
        mock_repo: MagicMock,
        mock_playlist_info: MagicMock,
    ) -> None:
        mock_repo.get_by_url.return_value = None
        mock_playlist_info.get_playlist_metadata.side_effect = APIError("timeout")

        with pytest.raises(APIError):
            service.create("https://music.youtube.com/playlist?list=PLbad")

    def test_create_unexpected_error_wraps_in_metadata_fetch_error(
        self,
        service: SubscriptionService,
        mock_repo: MagicMock,
        mock_playlist_info: MagicMock,
    ) -> None:
        mock_repo.get_by_url.return_value = None
        mock_playlist_info.get_playlist_metadata.side_effect = RuntimeError("boom")

        with pytest.raises(MetadataFetchError) as exc_info:
            service.create("https://music.youtube.com/playlist?list=PLbad")
        assert exc_info.value.upstream_error == "RuntimeError"

    def test_create_with_max_items(
        self,
        service: SubscriptionService,
        mock_repo: MagicMock,
        mock_playlist_info: MagicMock,
    ) -> None:
        mock_repo.get_by_url.return_value = None
        mock_playlist_info.get_playlist_metadata.return_value = PlaylistMetadata(
            title="Playlist", thumbnail_url=None
        )
        mock_repo.create.side_effect = lambda sub: sub

        result = service.create(
            "https://music.youtube.com/playlist?list=PLnew", max_items=5
        )

        assert result.max_items == 5


class TestUpdate:
    def test_update_success(
        self,
        service: SubscriptionService,
        mock_repo: MagicMock,
        sample_subscription: Subscription,
    ) -> None:
        mock_repo.update.return_value = sample_subscription

        result = service.update(sample_subscription.id, name="New Name")

        assert result == sample_subscription
        mock_repo.update.assert_called_once_with(
            sample_subscription.id, name="New Name"
        )

    def test_update_not_found(
        self, service: SubscriptionService, mock_repo: MagicMock
    ) -> None:
        mock_repo.update.return_value = None
        sub_id = uuid4()

        with pytest.raises(SubscriptionNotFoundError):
            service.update(sub_id, name="New Name")

    def test_update_empty_kwargs_returns_existing(
        self,
        service: SubscriptionService,
        mock_repo: MagicMock,
        sample_subscription: Subscription,
    ) -> None:
        mock_repo.get.return_value = sample_subscription

        result = service.update(sample_subscription.id)

        assert result == sample_subscription
        mock_repo.update.assert_not_called()
        mock_repo.get.assert_called_once()


class TestDelete:
    def test_delete_success(
        self, service: SubscriptionService, mock_repo: MagicMock
    ) -> None:
        mock_repo.delete.return_value = True
        sub_id = uuid4()

        service.delete(sub_id)

        mock_repo.delete.assert_called_once_with(sub_id)

    def test_delete_not_found(
        self, service: SubscriptionService, mock_repo: MagicMock
    ) -> None:
        mock_repo.delete.return_value = False
        sub_id = uuid4()

        with pytest.raises(SubscriptionNotFoundError):
            service.delete(sub_id)


class TestUpdateMetadataByUrl:
    def test_update_metadata_found(
        self,
        service: SubscriptionService,
        mock_repo: MagicMock,
        sample_subscription: Subscription,
    ) -> None:
        mock_repo.get_by_url.return_value = sample_subscription
        mock_repo.update.return_value = sample_subscription

        result = service.update_metadata_by_url(
            sample_subscription.url, "New Name", "https://example.com/new.jpg"
        )

        assert result is True
        mock_repo.update.assert_called_once_with(
            sample_subscription.id,
            name="New Name",
            thumbnail_url="https://example.com/new.jpg",
        )

    def test_update_metadata_not_found(
        self, service: SubscriptionService, mock_repo: MagicMock
    ) -> None:
        mock_repo.get_by_url.return_value = None

        result = service.update_metadata_by_url(
            "https://music.youtube.com/playlist?list=PLmissing",
            "Name",
            None,
        )

        assert result is False
        mock_repo.update.assert_not_called()
