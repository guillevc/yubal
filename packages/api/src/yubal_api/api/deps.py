"""FastAPI dependency injection factories.

This module provides type-safe dependency injection for FastAPI routes.
Dependencies are defined as Annotated types for clean, reusable injection.

Usage in routes:
    from yubal_api.api.deps import JobStoreDep, CookiesFileDep

    @router.get("/jobs")
    async def list_jobs(job_store: JobStoreDep) -> ...:
        ...
"""

from pathlib import Path
from typing import Annotated

from fastapi import Depends
from yubal import AudioCodec

from yubal_api.api.container import Services, get_services
from yubal_api.db.repository import SubscriptionRepository
from yubal_api.services.job_executor import JobExecutor
from yubal_api.services.job_store import JobStore
from yubal_api.services.playlist_info import PlaylistInfoService
from yubal_api.services.scheduler import Scheduler
from yubal_api.settings import Settings, get_settings

# -- Settings --

SettingsDep = Annotated[Settings, Depends(get_settings)]

# -- Service dependencies (request-scoped via app.state) --

ServicesDep = Annotated[Services, Depends(get_services)]


def _get_job_store(services: ServicesDep) -> JobStore:
    """Get job store from services container."""
    return services.job_store


def _get_job_executor(services: ServicesDep) -> JobExecutor:
    """Get job executor from services container."""
    return services.job_executor


def _get_repository(services: ServicesDep) -> SubscriptionRepository:
    """Get subscription repository from services container."""
    return services.repository


def _get_scheduler(services: ServicesDep) -> Scheduler:
    """Get scheduler from services container."""
    return services.scheduler


JobStoreDep = Annotated[JobStore, Depends(_get_job_store)]
JobExecutorDep = Annotated[JobExecutor, Depends(_get_job_executor)]
RepositoryDep = Annotated[SubscriptionRepository, Depends(_get_repository)]
SchedulerDep = Annotated[Scheduler, Depends(_get_scheduler)]

# -- Settings dependencies --

AudioFormatDep = Annotated[AudioCodec, Depends(lambda: get_settings().audio_format)]
CookiesFileDep = Annotated[Path, Depends(lambda: get_settings().cookies_file)]
YtdlpDirDep = Annotated[Path, Depends(lambda: get_settings().ytdlp_dir)]


def _get_playlist_info_service() -> PlaylistInfoService:
    """Get playlist info service for fetching playlist metadata."""
    settings = get_settings()
    cookies_path = settings.cookies_file if settings.cookies_file.exists() else None
    return PlaylistInfoService(cookies_path=cookies_path)


PlaylistInfoServiceDep = Annotated[
    PlaylistInfoService, Depends(_get_playlist_info_service)
]
