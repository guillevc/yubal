from enum import StrEnum


class JobStatus(StrEnum):
    """Status of a background job."""

    PENDING = "pending"  # Waiting to start
    FETCHING_INFO = "fetching_info"  # Extracting content metadata
    DOWNLOADING = "downloading"  # Downloading tracks (0-80%)
    IMPORTING = "importing"  # Beets import (80-100%)
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_finished(self) -> bool:
        return self in (self.COMPLETED, self.FAILED, self.CANCELLED)


class ProgressStep(StrEnum):
    """Steps in the sync workflow. Values match JobStatus."""

    FETCHING_INFO = "fetching_info"
    DOWNLOADING = "downloading"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"
