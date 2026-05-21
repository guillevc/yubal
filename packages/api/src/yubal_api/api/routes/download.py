"""Download endpoint for triggering a job via a simple query parameter.

Provides a convenient alternative to POST /api/jobs for external tools
(scripts, browser extensions, etc.) that prefer a URL-based interface
over a JSON request body.
"""

from fastapi import APIRouter, Query, status

from yubal_api.api.deps import JobExecutorDep
from yubal_api.api.exceptions import QueueFullError
from yubal_api.schemas.jobs import JobCreatedResponse, validate_youtube_music_url

router = APIRouter(tags=["download"])


@router.post(
    "/download",
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a download by URL",
    description=(
        "Queue a download job for a YouTube or YouTube Music URL. "
        "Accepts the URL as a query parameter for easy use from scripts "
        "and browser integrations. Returns 409 if the queue is full."
    ),
)
async def download(
    job_executor: JobExecutorDep,
    url: str = Query(
        description="YouTube or YouTube Music URL (playlist, album, or track)",
        examples=[
            "https://music.youtube.com/playlist?list=OLAK5uy_...",
            "https://www.youtube.com/watch?v=VIDEO_ID",
        ],
    ),
    max_items: int | None = Query(
        default=None,
        ge=1,
        le=10000,
        description="Maximum number of tracks to download",
    ),
) -> JobCreatedResponse:
    """Queue a download job for the given URL.

    The URL is validated against the same rules as POST /api/jobs.
    Returns the created job ID which can be tracked via GET /api/jobs
    or the SSE stream at GET /api/jobs/sse.
    """
    validated_url = validate_youtube_music_url(url)
    job = job_executor.create_and_start_job(validated_url, max_items)

    if job is None:
        raise QueueFullError()

    return JobCreatedResponse(id=job.id)
