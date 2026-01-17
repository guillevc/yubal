"""FastAPI dependency injection factories.

This module provides type-safe dependency injection for FastAPI routes.
Dependencies are defined as Annotated types for clean, reusable injection.

Usage in routes:
    from yubal_api.api.dependencies import JobStoreDep, CookiesFileDep

    @router.get("/jobs")
    async def list_jobs(job_store: JobStoreDep) -> ...:
        ...
"""

from pathlib import Path
from typing import Annotated

from fastapi import Depends
from yubal import AudioCodec

from yubal_api.api.services_container import get_services
from yubal_api.services.job_executor import JobExecutor
from yubal_api.services.job_store import JobStore
from yubal_api.settings import get_settings

# -- Service dependencies --


def _get_job_store() -> JobStore:
    return get_services().job_store


def _get_job_executor() -> JobExecutor:
    return get_services().job_executor


JobStoreDep = Annotated[JobStore, Depends(_get_job_store)]
JobExecutorDep = Annotated[JobExecutor, Depends(_get_job_executor)]

# -- Settings dependencies --

AudioFormatDep = Annotated[AudioCodec, Depends(lambda: get_settings().audio_format)]
CookiesFileDep = Annotated[Path, Depends(lambda: get_settings().cookies_file)]
YtdlpDirDep = Annotated[Path, Depends(lambda: get_settings().ytdlp_dir)]
