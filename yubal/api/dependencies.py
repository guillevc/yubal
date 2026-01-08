"""FastAPI dependency injection factories."""

import uuid
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from yubal.core.types import AudioFormat
from yubal.services.downloader import Downloader
from yubal.services.file_organizer import FileOrganizer
from yubal.services.job_executor import JobExecutor
from yubal.services.job_store import JobStore
from yubal.services.metadata_enricher import MetadataEnricher
from yubal.services.metadata_patcher import MetadataPatcher
from yubal.services.sync import AlbumSyncService, PlaylistSyncService
from yubal.services.tagger import Tagger
from yubal.settings import get_settings


@cache
def get_job_store() -> JobStore:
    """Get cached job store instance (created on first call)."""
    settings = get_settings()
    return JobStore(
        clock=lambda: datetime.now(settings.timezone),
        id_generator=lambda: str(uuid.uuid4()),
    )


def get_audio_format() -> AudioFormat:
    """Get audio format from settings."""
    return get_settings().audio_format


def get_cookies_file() -> Path:
    """Get cookies file path from settings."""
    return get_settings().cookies_file


def get_ytdlp_dir() -> Path:
    """Get yt-dlp directory from settings."""
    return get_settings().ytdlp_dir


def get_downloader() -> Downloader:
    """Factory for creating Downloader with settings."""
    settings = get_settings()
    return Downloader(
        audio_format=settings.audio_format,
        cookies_file=settings.cookies_file,
    )


def get_tagger() -> Tagger:
    """Factory for creating Tagger with settings."""
    settings = get_settings()
    return Tagger(
        beets_config=settings.beets_config,
        library_dir=settings.library_dir,
        beets_db=settings.beets_db,
    )


def get_album_sync_service() -> AlbumSyncService:
    """Factory for creating AlbumSyncService with injected dependencies."""
    settings = get_settings()
    return AlbumSyncService(
        downloader=get_downloader(),
        tagger=get_tagger(),
        temp_dir=settings.temp_dir,
    )


def get_playlist_sync_service() -> PlaylistSyncService:
    """Factory for creating PlaylistSyncService with injected dependencies."""
    settings = get_settings()
    return PlaylistSyncService(
        downloader=get_downloader(),
        enricher=MetadataEnricher(),
        patcher=MetadataPatcher(),
        file_organizer=FileOrganizer(playlists_dir=settings.playlists_dir),
        temp_dir=settings.temp_dir,
        playlists_dir=settings.playlists_dir,
    )


@cache
def get_job_executor() -> JobExecutor:
    """Get cached job executor instance (singleton).

    JobExecutor maintains internal state (background tasks, cancel tokens)
    so it must be a singleton across the application lifecycle.
    """
    return JobExecutor(
        job_store=get_job_store(),
        album_sync_service=get_album_sync_service(),
        playlist_sync_service=get_playlist_sync_service(),
    )


# Type aliases for FastAPI dependency injection
CookiesFileDep = Annotated[Path, Depends(get_cookies_file)]
YtdlpDirDep = Annotated[Path, Depends(get_ytdlp_dir)]
JobStoreDep = Annotated[JobStore, Depends(get_job_store)]
AudioFormatDep = Annotated[AudioFormat, Depends(get_audio_format)]
AlbumSyncServiceDep = Annotated[AlbumSyncService, Depends(get_album_sync_service)]
PlaylistSyncServiceDep = Annotated[
    PlaylistSyncService, Depends(get_playlist_sync_service)
]
JobExecutorDep = Annotated[JobExecutor, Depends(get_job_executor)]
