"""FastAPI application factory and configuration."""

import logging
import mimetypes
import shutil
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from importlib.metadata import version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from rich.console import Console
from rich.logging import RichHandler

from yubal_api.api.exceptions import register_exception_handlers
from yubal_api.api.routes import cookies, health, jobs, logs
from yubal_api.api.services_container import Services, clear_services, set_services
from yubal_api.services.job_executor import JobExecutor
from yubal_api.services.job_store import JobStore
from yubal_api.services.log_buffer import (
    BufferHandler,
    clear_log_buffer,
    get_log_buffer,
)
from yubal_api.settings import get_settings


def setup_logging() -> None:
    """Configure logging with Rich handler for all loggers including uvicorn."""
    settings = get_settings()
    console = Console(force_terminal=True)
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


setup_logging()
logger = logging.getLogger(__name__)


def create_services() -> Services:
    """Create all application services with proper dependency wiring."""
    settings = get_settings()

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
    )

    return Services(
        job_store=job_store,
        job_executor=job_executor,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    # Startup: initialize services
    logger.info("Starting application...")
    services = create_services()
    set_services(services)
    app.state.services = services  # Also store in app.state for direct access
    logger.info("Services initialized")

    yield

    # Shutdown: cleanup
    logger.info("Shutting down...")
    services.close()
    clear_services()
    clear_log_buffer()

    temp = get_settings().temp
    if temp.exists():
        logger.info("Cleaning up temp directory: %s", temp)
        shutil.rmtree(temp, ignore_errors=True)

    logger.info("Shutdown complete")


def create_api() -> FastAPI:
    """Create the API sub-application."""
    api = FastAPI(
        title="yubal API",
        description="YouTube Music Downloader API",
        version=version("yubal_api"),
    )

    # Register exception handlers
    register_exception_handlers(api)

    # API routes
    api.include_router(health.router)
    api.include_router(jobs.router)
    api.include_router(logs.router)
    api.include_router(cookies.router)

    return api


def create_app() -> FastAPI:
    """Create and configure the main FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="yubal",
        lifespan=lifespan,
        debug=settings.debug,
    )

    # CORS middleware (type ignore needed due to Starlette typing limitations)
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API sub-app at /api
    app.mount("/api", create_api())

    # Static files from YUBAL_ROOT/web/dist
    # Fix MIME types for Windows (registry defaults .js to text/plain)
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("text/css", ".css")

    web_build = get_settings().root / "web" / "dist"
    if web_build.exists():
        app.mount("/", StaticFiles(directory=web_build, html=True), name="static")

    return app


# Create app instance for uvicorn
app = create_app()
