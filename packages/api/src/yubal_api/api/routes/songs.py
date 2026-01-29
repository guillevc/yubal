"""Song API endpoints."""

from fastapi import APIRouter, HTTPException, status

from yubal import APIError
from yubal.client import YTMusicClient
from yubal_api.settings import get_settings

router = APIRouter(prefix="/songs", tags=["songs"])


@router.get("/{video_id}/related", status_code=status.HTTP_200_OK)
async def get_song_related(video_id: str) -> list[dict]:
    """Get related content for a song by video ID."""
    settings = get_settings()
    client = YTMusicClient(cookies_path=settings.cookies_file)

    try:
        related = client.get_song_related(video_id)
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return related
