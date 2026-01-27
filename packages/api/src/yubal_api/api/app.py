"""FastAPI application factory and configuration."""

import logging
import mimetypes
import shutil
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from importlib.metadata import version

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from rich.console import Console
from rich.logging import RichHandler
from yubal import cleanup_part_files

from yubal_api.api.exceptions import register_exception_handlers
from yubal_api.api.routes import cookies, health, jobs, logs, sync
from yubal_api.api.services_container import Services
from yubal_api.db import DB_FILE, SyncRepository, create_db_engine, init_db
from yubal_api.services.job_executor import JobExecutor
from yubal_api.services.job_store import JobStore
from yubal_api.services.log_buffer import (
    BufferHandler,
    clear_log_buffer,
    get_log_buffer,
)
from yubal_api.services.shutdown import ShutdownCoordinator
from yubal_api.services.sync_scheduler import SyncScheduler
from yubal_api.settings import get_settings

# Global reference for shutdown suppression
_rich_console: Console | None = None


def setup_logging() -> None:
    """Configure logging with Rich handler for all loggers including uvicorn."""
    global _rich_console

    settings = get_settings()
    console = Console(force_terminal=True)
    _rich_console = console  # Store for shutdown suppression

    handler = RichHandler(
        console=console, rich_tracebacks=True, show_path=False, markup=True
    )
    handler.setFormatter(logging.Formatter("%(name)s - %(message)s", datefmt="[%X]"))

    # Configure root logger
    logging.root.handlers = [handler]
    logging.root.setLevel(settings.log_level)

    # Configure uvicorn loggers to use Rich
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = [handler]
        uvicorn_logger.propagate = False

    # Add buffer handler to capture logs for SSE streaming
    buffer_handler = BufferHandler(get_log_buffer())
    buffer_handler.setLevel(logging.INFO)
    logging.getLogger("yubal").addHandler(buffer_handler)
    logging.getLogger("yubal_api").addHandler(buffer_handler)


def suppress_logging() -> None:
    """Suppress most logging output during shutdown.

    Keeps ERROR level visible but suppresses INFO/WARNING to prevent
    routine messages from appearing after the shell prompt returns.
    """
    # Keep errors visible, suppress INFO/WARNING
    for handler in logging.root.handlers:
        handler.setLevel(logging.ERROR)

    # Also suppress uvicorn loggers
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        for handler in logging.getLogger(name).handlers:
            handler.setLevel(logging.ERROR)

    # Quiet the Rich console
    if _rich_console:
        _rich_console.quiet = True


setup_logging()
logger = logging.getLogger(__name__)


def create_services(sync_repository: SyncRepository) -> Services:
    """Create all application services with proper dependency wiring.

    Args:
        sync_repository: Repository for sync database operations.

    Returns:
        Services container with all application services.
    """
    settings = get_settings()

    # Create shutdown coordinator
    shutdown_coordinator = ShutdownCoordinator()

    # Create job management services
    job_store = JobStore(
        clock=lambda: datetime.now(settings.timezone),
        id_generator=lambda: str(uuid.uuid4()),
    )

    job_executor = JobExecutor(
        job_store=job_store,
        base_path=settings.data,
        audio_format=settings.audio_format,
        cookies_path=settings.cookies_file,
        fetch_lyrics=settings.fetch_lyrics,
    )

    # Create sync scheduler
    sync_scheduler = SyncScheduler(
        repository=sync_repository,
        job_store=job_store,
    )

    # Wire up coordinator with executor
    shutdown_coordinator.set_job_executor(job_executor)

    return Services(
        job_store=job_store,
        job_executor=job_executor,
        shutdown_coordinator=shutdown_coordinator,
        sync_repository=sync_repository,
        sync_scheduler=sync_scheduler,
    )


def create_api_router() -> APIRouter:
    """Create the API router with all routes under /api prefix."""
    api_router = APIRouter(prefix="/api")
    api_router.include_router(health.router)
    api_router.include_router(jobs.router)
    api_router.include_router(logs.router)
    api_router.include_router(cookies.router)
    api_router.include_router(sync.router)
    return api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()
    logger.info("Starting application...")

    # Initialize database
    db_path = settings.config / DB_FILE
    engine = create_db_engine(db_path)
    init_db(engine)
    logger.info("Database initialized at %s", db_path)

    # Create services with database repository
    sync_repository = SyncRepository(engine)
    services = create_services(sync_repository)
    app.state.services = services
    logger.info("Services initialized")

    # Start scheduler
    services.sync_scheduler.start()

    yield

    # Shutdown sequence
    # Stop scheduler first
    await services.sync_scheduler.stop()

    # Cancel any running jobs
    services.shutdown_coordinator.begin_shutdown()

    # Suppress logging to prevent post-prompt messages
    suppress_logging()

    # Clean up .part files from incomplete downloads (delegated to yubal)
    cleanup_part_files(settings.data)

    # Clean up log buffer
    clear_log_buffer()

    # Clean temp directory
    if settings.temp.exists():
        shutil.rmtree(settings.temp, ignore_errors=True)

    services.close()


def create_app() -> FastAPI:
    """Create and configure the main FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="yubal",
        description="YouTube Music Downloader API",
        version=version("yubal_api"),
        lifespan=lifespan,
        debug=settings.debug,
    )

    # Register exception handlers
    register_exception_handlers(app)

    # CORS middleware (type ignore needed due to Starlette typing limitations)
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes under /api prefix
    app.include_router(create_api_router())

    # Static files from YUBAL_ROOT/web/dist
    # Fix MIME types for Windows (registry defaults .js to text/plain)
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")

    web_build = settings.root / "web" / "dist"
    if web_build.exists():
        app.mount("/", StaticFiles(directory=web_build, html=True), name="static")

    return app


# Create app instance for uvicorn
app = create_app()
