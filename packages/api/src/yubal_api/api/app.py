"""FastAPI application factory and configuration."""

import asyncio
import logging
import mimetypes
import shutil
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from importlib.metadata import version
from importlib.resources import files
from typing import Any

from alembic import command
from alembic.config import Config
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from pydantic import TypeAdapter
from rich.console import Console
from rich.logging import RichHandler
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope
from yubal import cleanup_part_files

from yubal_api.api.container import Services
from yubal_api.api.exceptions import register_exception_handlers
from yubal_api.api.routes import cookies, health, jobs, logs, scheduler, subscriptions
from yubal_api.db import SubscriptionRepository, create_db_engine
from yubal_api.schemas.jobs import (
    ClearedEvent,
    CreatedEvent,
    DeletedEvent,
    SnapshotEvent,
    UpdatedEvent,
)
from yubal_api.schemas.logs import LogEntry
from yubal_api.services.job_event_bus import JobEventBus
from yubal_api.services.job_executor import JobExecutor
from yubal_api.services.job_store import JobStore
from yubal_api.services.log_buffer import BufferHandler, LogBuffer
from yubal_api.services.playlist_info import PlaylistInfoService
from yubal_api.services.scheduler import Scheduler
from yubal_api.services.shutdown import ShutdownCoordinator
from yubal_api.services.subscription_service import SubscriptionService
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


def setup_log_streaming(log_buffer: LogBuffer) -> None:
    """Attach buffer handler to capture logs for SSE streaming."""
    buffer_handler = BufferHandler(log_buffer)
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


def run_migrations() -> None:
    """Run database migrations using Alembic."""
    alembic_ini = files("yubal_api").joinpath("alembic.ini")
    alembic_cfg = Config(str(alembic_ini))
    command.upgrade(alembic_cfg, "head")


def create_services(repository: SubscriptionRepository) -> Services:
    """Create all application services with proper dependency wiring.

    Args:
        repository: Repository for subscription database operations.

    Returns:
        Services container with all application services.
    """
    settings = get_settings()

    # Create event bus and log buffer
    job_event_bus = JobEventBus()
    log_buffer = LogBuffer()

    # Attach log streaming before services start logging
    setup_log_streaming(log_buffer)

    # Create shutdown coordinator
    shutdown_coordinator = ShutdownCoordinator()

    # Create job management services
    job_store = JobStore(
        clock=lambda: datetime.now(settings.timezone),
        id_generator=lambda: str(uuid.uuid4()),
        event_bus=job_event_bus,
    )

    job_executor = JobExecutor(
        job_store=job_store,
        base_path=settings.data,
        audio_format=settings.audio_format,
        cookies_path=settings.cookies_file,
        fetch_lyrics=settings.fetch_lyrics,
        apply_replaygain=settings.replaygain,
        subscription_repository=repository,
    )

    # Create subscription service
    cookies_path = settings.cookies_file if settings.cookies_file.exists() else None
    playlist_info = PlaylistInfoService(cookies_path=cookies_path)
    subscription_service = SubscriptionService(
        repository=repository,
        playlist_info=playlist_info,
    )

    # Create scheduler
    scheduler_service = Scheduler(
        repository=repository,
        job_executor=job_executor,
        settings=settings,
    )

    # Wire up coordinator with executor
    shutdown_coordinator.set_job_executor(job_executor)

    return Services(
        job_store=job_store,
        job_executor=job_executor,
        shutdown_coordinator=shutdown_coordinator,
        repository=repository,
        subscription_service=subscription_service,
        scheduler=scheduler_service,
        job_event_bus=job_event_bus,
        log_buffer=log_buffer,
    )


def create_api_router() -> APIRouter:
    """Create the API router with all routes under /api prefix."""
    api_router = APIRouter(prefix="/api")
    api_router.include_router(health.router)
    api_router.include_router(jobs.router)
    api_router.include_router(logs.router)
    api_router.include_router(cookies.router)
    api_router.include_router(subscriptions.router)
    api_router.include_router(scheduler.router)
    return api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()
    logger.info("Starting application...")

    # Run database migrations (in thread to avoid blocking event loop)
    await asyncio.to_thread(run_migrations)
    logger.info("Database migrations complete")

    # Create database engine
    db_path = settings.db_path
    engine = create_db_engine(db_path)

    # Create services with database repository
    repository = SubscriptionRepository(engine)
    services = create_services(repository)
    app.state.services = services
    logger.info("Services initialized")

    # Start scheduler
    services.scheduler.start()

    yield

    # Shutdown sequence
    # Stop scheduler first
    await services.scheduler.stop()

    # Cancel any running jobs
    services.shutdown_coordinator.begin_shutdown()

    # Suppress logging to prevent post-prompt messages
    suppress_logging()

    # Clean up .part files from incomplete downloads (delegated to yubal)
    cleanup_part_files(settings.data)

    # Clean temp directory
    if settings.temp.exists():
        shutil.rmtree(settings.temp, ignore_errors=True)

    services.close()


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Generate OpenAPI schema with SSE event types included.

    SSE event schemas aren't auto-discovered by FastAPI since they're
    returned via StreamingResponse. This function injects them into
    the OpenAPI schema so TypeScript types are generated.
    """
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Inject SSE event schemas (not auto-discovered due to StreamingResponse)
    sse_models = [
        # Jobs SSE events
        (SnapshotEvent, "SnapshotEvent"),
        (CreatedEvent, "CreatedEvent"),
        (UpdatedEvent, "UpdatedEvent"),
        (DeletedEvent, "DeletedEvent"),
        (ClearedEvent, "ClearedEvent"),
        # Logs SSE event
        (LogEntry, "LogEntry"),
    ]
    for model, name in sse_models:
        json_schema = TypeAdapter(model).json_schema(
            ref_template="#/components/schemas/{model}"
        )
        defs = json_schema.pop("$defs", {})
        schema["components"]["schemas"].update(defs)
        schema["components"]["schemas"][name] = json_schema

    # Define SSE endpoint response schemas
    sse_endpoints = {
        "/api/jobs/sse": {
            "schema": {
                "oneOf": [
                    {"$ref": "#/components/schemas/SnapshotEvent"},
                    {"$ref": "#/components/schemas/CreatedEvent"},
                    {"$ref": "#/components/schemas/UpdatedEvent"},
                    {"$ref": "#/components/schemas/DeletedEvent"},
                    {"$ref": "#/components/schemas/ClearedEvent"},
                ]
            },
        },
        "/api/logs/sse": {
            "schema": {"$ref": "#/components/schemas/LogEntry"},
        },
    }

    # Inject response schemas into SSE endpoints
    for path, config in sse_endpoints.items():
        if path in schema["paths"]:
            schema["paths"][path]["get"]["responses"]["200"]["content"] = {
                "text/event-stream": {
                    "schema": config["schema"],
                }
            }

    app.openapi_schema = schema
    return schema


class SPAStaticFiles(StaticFiles):
    """StaticFiles configured for SPA fallback to index.html."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        """Serve static files, falling back to index.html for SPA routes."""
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as ex:
            if ex.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


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

    # Custom OpenAPI schema to include SSE event types
    app.openapi = lambda: custom_openapi(app)  # type: ignore[method-assign]

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
        app.mount("/", SPAStaticFiles(directory=web_build, html=True), name="spa")

    return app


# Create app instance for uvicorn
app = create_app()
