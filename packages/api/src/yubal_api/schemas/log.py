"""Structured logging schemas for frontend consumption."""

from typing import Literal

from pydantic import BaseModel, Field

# Discriminator type for frontend type narrowing
LogEntryType = Literal[
    "header", "phase", "stats", "progress", "status", "file", "default"
]

# Skip reason string literals for TypeScript type generation
# Must match SkipReason enum in yubal.models.enums
SkipReasonType = Literal[
    "file_exists",
    "unsupported_video_type",
    "no_video_id",
    "region_unavailable",
    "no_album_match",
]

# Stats type discriminator for frontend rendering
StatsType = Literal["extraction", "download"]


class LogStats(BaseModel):
    """Statistics for batch operations.

    Uses a discriminator field (stats_type) for frontend type narrowing,
    and dictionary-based skip reason counts for scalability.

    Attributes:
        stats_type: Discriminator indicating extraction or download stats.
        success: Number of successful operations.
        failed: Number of failed operations.
        skipped_by_reason: Count of skipped items by reason.
    """

    stats_type: StatsType = Field(
        ..., description="Type of stats: 'extraction' or 'download'"
    )
    success: int = 0
    failed: int = 0
    skipped_by_reason: dict[SkipReasonType, int] = Field(
        default_factory=dict,
        description="Count of skipped items by reason",
    )

    @property
    def skipped(self) -> int:
        """Total number of skipped items across all reasons."""
        return sum(self.skipped_by_reason.values())


class LogEntry(BaseModel):
    """Structured log entry sent to frontend via SSE.

    Each log line from the backend is serialized as JSON using this schema.
    The frontend parses these entries and applies theme-aware styling.

    The `entry_type` field enables discriminated union pattern matching
    in TypeScript for exhaustive type narrowing.
    """

    # Discriminator for frontend type narrowing
    entry_type: LogEntryType = Field(
        "default", description="Entry type for discriminated union matching"
    )

    # Required fields
    timestamp: str = Field(..., description="Log timestamp in HH:MM:SS format")
    level: str = Field(..., description="Log level: DEBUG, INFO, WARNING, ERROR")
    message: str = Field(..., description="Human-readable log message")

    # Optional structured fields for enhanced frontend rendering
    phase: str | None = Field(
        None, description="Current operation phase: extracting, downloading, composing"
    )
    phase_num: int | None = Field(
        None, description="Phase number (1, 2, 3)", ge=1, le=3
    )
    event_type: str | None = Field(
        None, description="Specific event type for granular tracking"
    )
    current: int | None = Field(
        None, description="Current item index in progress (0-indexed)", ge=0
    )
    total: int | None = Field(
        None, description="Total number of items to process", ge=0
    )
    status: Literal["success", "skipped", "failed"] | None = Field(
        None, description="Operation result status"
    )
    stats: LogStats | None = Field(
        None, description="Aggregate statistics for batch operations"
    )
    file_path: str | None = Field(
        None, description="Path to generated or downloaded file"
    )
    file_type: str | None = Field(None, description="Type of file: m3u, cover, audio")
    track_title: str | None = Field(None, description="Track title being processed")
    track_artist: str | None = Field(None, description="Track artist name")
    header: str | None = Field(
        None, description="Section header text for visual separation"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "entry_type": "phase",
                    "timestamp": "11:09:53",
                    "level": "INFO",
                    "message": "Extracting metadata from playlist",
                    "phase": "extracting",
                    "phase_num": 1,
                },
                {
                    "entry_type": "progress",
                    "timestamp": "11:09:54",
                    "level": "INFO",
                    "message": "Queen - Bohemian Rhapsody",
                    "current": 1,
                    "total": 10,
                    "event_type": "track_download",
                    "track_title": "Bohemian Rhapsody",
                    "track_artist": "Queen",
                },
                {
                    "entry_type": "stats",
                    "timestamp": "11:09:55",
                    "level": "INFO",
                    "message": "Downloads complete",
                    "stats": {
                        "stats_type": "download",
                        "success": 8,
                        "failed": 0,
                        "skipped_by_reason": {"file_exists": 2},
                    },
                },
            ]
        }
    }
