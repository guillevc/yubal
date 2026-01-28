"""Database repository for subscriptions."""

from uuid import UUID

from sqlalchemy import Engine
from sqlmodel import Session, col, select

from yubal_api.db.models import Subscription, SubscriptionType


class SubscriptionRepository:
    """Repository for subscription database operations."""

    def __init__(self, engine: Engine) -> None:
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
