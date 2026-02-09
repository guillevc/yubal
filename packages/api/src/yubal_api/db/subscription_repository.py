"""Database repository for subscriptions."""

from uuid import UUID

from sqlalchemy import Engine
from sqlmodel import Session, col, select

from yubal_api.db.subscription import Subscription, SubscriptionFields, SubscriptionType


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

    def update(self, id: UUID, fields: SubscriptionFields) -> Subscription | None:
        """Update subscription fields by ID. Returns None if not found."""
        with Session(self._engine) as session:
            subscription = session.get(Subscription, id)
            if subscription is None:
                return None
            for key, value in fields.items():
                setattr(subscription, key, value)
            session.commit()
            session.refresh(subscription)
            return subscription

    def delete(self, id: UUID) -> bool:
        """Delete subscription by ID. Returns True if deleted, False if not found."""
        with Session(self._engine) as session:
            subscription = session.get(Subscription, id)
            if subscription is None:
                return False
            session.delete(subscription)
            session.commit()
            return True

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
