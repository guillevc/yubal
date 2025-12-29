import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from yubal.services.downloader import Downloader
from yubal.services.job_store import JobStore
from yubal.services.sync import SyncService
from yubal.services.tagger import Tagger
from yubal.settings import Settings, get_settings

# Global singleton instance
job_store = JobStore(
    clock=lambda: datetime.now(UTC),
    id_generator=lambda: str(uuid.uuid4()),
)


def get_job_store() -> JobStore:
    return job_store


SettingsDep = Annotated[Settings, Depends(get_settings)]
JobStoreDep = Annotated[JobStore, Depends(get_job_store)]


def get_sync_service(settings: SettingsDep) -> SyncService:
    """Factory for creating SyncService with injected dependencies."""
    return SyncService(
        library_dir=settings.library_dir,
        beets_config=settings.beets_config,
        audio_format=settings.audio_format,
        temp_dir=settings.temp_dir,
        downloader=Downloader(
            audio_format=settings.audio_format,
            cookies_file=settings.cookies_file,
        ),
        tagger=Tagger(
            beets_config=settings.beets_config,
            library_dir=settings.library_dir,
            beets_db=settings.beets_db,
        ),
    )


SyncServiceDep = Annotated[SyncService, Depends(get_sync_service)]
