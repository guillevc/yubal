"""FastAPI dependency injection factories."""

from pathlib import Path
from typing import Annotated

from fastapi import Depends
from yubal import AudioCodec

from yubal_api.api.services_container import get_services
from yubal_api.services.job_executor import JobExecutor
from yubal_api.services.job_store import JobStore
from yubal_api.settings import get_settings


def _get_job_store() -> JobStore:
    return get_services().job_store


def _get_job_executor() -> JobExecutor:
    return get_services().job_executor


def _get_audio_format() -> AudioCodec:
    return get_settings().audio_format


def _get_cookies_file() -> Path:
    return get_settings().cookies_file


def _get_ytdlp_dir() -> Path:
    return get_settings().ytdlp_dir


# Type aliases for FastAPI dependency injection
CookiesFileDep = Annotated[Path, Depends(_get_cookies_file)]
YtdlpDirDep = Annotated[Path, Depends(_get_ytdlp_dir)]
JobStoreDep = Annotated[JobStore, Depends(_get_job_store)]
AudioFormatDep = Annotated[AudioCodec, Depends(_get_audio_format)]
JobExecutorDep = Annotated[JobExecutor, Depends(_get_job_executor)]
