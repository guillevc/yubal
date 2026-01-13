"""Services container for dependency injection.

This module is separate from app.py to avoid circular imports.
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from yubal_api.services.job_executor import JobExecutor
    from yubal_api.services.job_store import JobStore


@dataclass
class Services:
    """Container for application services with proper lifecycle management.

    All services are created at startup and cleaned up at shutdown.
    """

    job_store: "JobStore"
    job_executor: "JobExecutor"

    def close(self) -> None:
        """Clean up resources. Called at application shutdown."""
        logger.info("Services cleaned up")


# Module-level services container, set by lifespan
_services: Services | None = None


def get_services() -> Services:
    """Get the services container.

    Raises RuntimeError if called before lifespan initialization.
    """
    if _services is None:
        raise RuntimeError("Services not initialized. Is the app running?")
    return _services


def set_services(services: Services) -> None:
    """Set the services container. Called during app startup."""
    global _services
    _services = services


def clear_services() -> None:
    """Clear the services container. Called during app shutdown."""
    global _services
    _services = None
