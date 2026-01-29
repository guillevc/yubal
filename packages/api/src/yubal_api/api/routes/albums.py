"""Album API endpoints."""

from fastapi import APIRouter, HTTPException, status

from yubal import APIError
from yubal.client import YTMusicClient
from yubal_api.settings import get_settings

router = APIRouter(prefix="/albums", tags=["albums"])


@router.get("/{browse_id}", status_code=status.HTTP_200_OK)
async def get_album(browse_id: str) -> dict:
    """Get album details and tracks by browse ID."""
    settings = get_settings()
    client = YTMusicClient(cookies_path=settings.cookies_file)

    try:
        album = client.get_album(browse_id)
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return album.model_dump(by_alias=True)
