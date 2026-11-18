"""Artist endpoints: search artists, list releases, queue discography downloads."""

from fastapi import APIRouter, Query, status
from yubal import ArtistRelease as CoreArtistRelease
from yubal.models.ytmusic import Thumbnail

from yubal_api.api.deps import ArtistServiceDep, JobExecutorDep
from yubal_api.api.exceptions import ErrorResponse, QueueFullError
from yubal_api.schemas.artists import (
    ArtistRelease,
    ArtistReleasesResponse,
    ArtistSearchResponse,
    ArtistSummary,
    QueueArtistReleasesRequest,
    QueueArtistReleasesResponse,
)

router = APIRouter(prefix="/artists", tags=["artists"])


def _largest_thumbnail(thumbnails: list[Thumbnail]) -> str | None:
    if not thumbnails:
        return None
    return max(thumbnails, key=lambda t: t.width * t.height).url


def _to_release(release: CoreArtistRelease) -> ArtistRelease | None:
    if not release.url:
        return None
    return ArtistRelease(
        title=release.title,
        type=release.type,
        year=release.year,
        url=release.url,
        thumbnail_url=_largest_thumbnail(release.thumbnails),
    )


@router.get(
    "/search",
    responses={404: {"model": ErrorResponse, "description": "No artists found"}},
)
def search_artists(
    artists: ArtistServiceDep,
    q: str = Query(min_length=1, max_length=200, description="Artist name"),
) -> ArtistSearchResponse:
    """Search YouTube Music for artists by name (best match first)."""
    results = artists.search(q)
    return ArtistSearchResponse(
        artists=[
            ArtistSummary(
                channel_id=r.browse_id,
                name=r.artist,
                thumbnail_url=_largest_thumbnail(r.thumbnails),
            )
            for r in results
        ]
    )


@router.get(
    "/{channel_id}/releases",
    responses={404: {"model": ErrorResponse, "description": "Artist not found"}},
)
def get_artist_releases(
    channel_id: str,
    artists: ArtistServiceDep,
) -> ArtistReleasesResponse:
    """List all albums and singles of an artist, with downloadable URLs."""
    discography = artists.get_discography(channel_id)
    return ArtistReleasesResponse(
        channel_id=discography.channel_id,
        name=discography.name,
        thumbnail_url=_largest_thumbnail(discography.thumbnails),
        albums=[r for a in discography.albums if (r := _to_release(a))],
        singles=[r for s in discography.singles if (r := _to_release(s))],
    )


@router.post(
    "/jobs",
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse, "description": "Queue is full"}},
)
async def queue_artist_releases(
    request: QueueArtistReleasesRequest,
    job_executor: JobExecutorDep,
) -> QueueArtistReleasesResponse:
    """Queue one download job per release.

    Jobs run sequentially through the regular job queue. If the queue fills
    up partway through, the remaining releases are reported as skipped.
    Returns 409 only if no job could be created.
    """
    job_ids: list[str] = []
    for i, url in enumerate(request.urls):
        job = job_executor.create_and_start_job(url)
        if job is None:
            if not job_ids:
                raise QueueFullError()
            return QueueArtistReleasesResponse(
                job_ids=job_ids, skipped=len(request.urls) - i
            )
        job_ids.append(job.id)
    return QueueArtistReleasesResponse(job_ids=job_ids)
