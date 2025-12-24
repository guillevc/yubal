"""FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="yubal API",
    description="YouTube Album Downloader API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from yubal.api.routes import sync  # noqa: E402

app.include_router(sync.router, prefix="/api/v1", tags=["sync"])


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy")


# Static file serving for production frontend
# Path: project root / web / dist
WEB_BUILD = Path(__file__).parent.parent.parent / "web" / "dist"
if WEB_BUILD.exists():
    app.mount("/", StaticFiles(directory=WEB_BUILD, html=True), name="static")
