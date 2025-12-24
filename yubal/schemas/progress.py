"""Progress event schemas."""

from typing import Any

from pydantic import BaseModel


class ProgressEventSchema(BaseModel):
    """Schema for progress events sent via SSE."""

    step: str
    message: str
    progress: float | None = None
    details: dict[str, Any] | None = None

    class Config:
        """Pydantic config."""

        from_attributes = True
