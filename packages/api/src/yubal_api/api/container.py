"""Services container for dependency injection.

This module provides the Services container and dependency injection
utilities for accessing services from FastAPI routes via app.state.
"""

import logging
from dataclasses import dataclass

from fastapi import Request

from yubal_api.db.repository import SubscriptionRepository
from yubal_api.services.job_executor import JobExecutor
from yubal_api.services.job_store import JobStore
from yubal_api.services.scheduler import Scheduler
from yubal_api.services.shutdown import ShutdownCoordinator

logger = logging.getLogger(__name__)


@dataclass
class Services:
    """Container for application services with proper lifecycle management.

    All services are created at startup and cleaned up at shutdown.
    Stored in FastAPI's app.state for proper request scoping.
    """

    job_store: JobStore
    job_executor: JobExecutor
    shutdown_coordinator: ShutdownCoordinator
    repository: SubscriptionRepository
    scheduler: Scheduler

    def close(self) -> None:
        """Clean up resources. Called at application shutdown."""
        logger.info("Services cleaned up")


def get_services(request: Request) -> Services:
    """Get services from request's app state (dependency injection).

    Args:
        request: FastAPI request object.

    Returns:
        Services container.

    Raises:
        RuntimeError: If services not initialized (app not running).
    """
    services = getattr(request.app.state, "services", None)
    if services is None:
        raise RuntimeError("Services not initialized. Is the app running?")
    return services
