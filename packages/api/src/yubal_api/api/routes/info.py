"""Content info endpoint for quick URL metadata lookup."""

from fastapi import APIRouter, Query

from yubal_api.api.deps import PlaylistInfoServiceDep
from yubal_api.domain.job import ContentInfo

router = APIRouter(tags=["info"])


@router.get("/info")
def get_content_info(
    playlist_info: PlaylistInfoServiceDep,
    url: str = Query(description="YouTube Music URL (playlist, album, or track)"),
) -> ContentInfo:
    """Get metadata for a YouTube Music URL.

    Returns title, artist, kind, track count, year, and thumbnail
    from a single API call without running the full extraction pipeline.
    """
    return playlist_info.get_content_info(url)
