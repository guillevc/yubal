"""Search API schemas."""

from typing import Any

from pydantic import BaseModel, Field


class SearchResponse(BaseModel):
    """Response for search results."""

    results: list[dict[str, Any]] = Field(default_factory=list)


class SearchSuggestionsResponse(BaseModel):
    """Response for search suggestions."""

    suggestions: list[Any] = Field(default_factory=list)
