from fastapi import APIRouter

from yubal.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy")
