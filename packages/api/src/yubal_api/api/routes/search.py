"""Search API endpoints."""

from fastapi import APIRouter, HTTPException, Query, status

from yubal import APIError
from yubal.client import YTMusicClient
from yubal_api.schemas.search import SearchResponse, SearchSuggestionsResponse
from yubal_api.settings import get_settings

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", status_code=status.HTTP_200_OK)
async def search(
    query: str = Query(..., min_length=1, description="Search query"),
    search_filter: str | None = Query(
        None,
        alias="filter",
        description="Filter for item types (songs, videos, albums, artists, playlists)",
    ),
    scope: str | None = Query(
        None, description="Search scope (library, uploads)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    ignore_spelling: bool | None = Query(
        None, description="Ignore YouTube Music spelling suggestions"
    ),
) -> SearchResponse:
    """Search YouTube Music using ytmusicapi."""
    settings = get_settings()
    client = YTMusicClient(cookies_path=settings.cookies_file)

    try:
        results = client.search(
            query,
            filter=search_filter,
            scope=scope,
            limit=limit,
            ignore_spelling=ignore_spelling,
        )
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return SearchResponse(results=results)


@router.get("/suggestions", status_code=status.HTTP_200_OK)
async def search_suggestions(
    query: str = Query(..., min_length=1, description="Search query"),
    detailed_runs: bool = Query(
        False, description="Return detailed runs for each suggestion"
    ),
) -> SearchSuggestionsResponse:
    """Get search suggestions from YouTube Music."""
    settings = get_settings()
    client = YTMusicClient(cookies_path=settings.cookies_file)

    try:
        suggestions = client.search_suggestions(query, detailed_runs=detailed_runs)
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return SearchSuggestionsResponse(suggestions=suggestions)
