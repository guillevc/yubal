"""Extraction state tracking for CLI commands."""

from dataclasses import dataclass, field

from yubal.models.enums import SkipReason
from yubal.models.progress import ExtractProgress
from yubal.models.track import TrackMetadata, UnavailableTrack


@dataclass
class ExtractionState:
    """Accumulates state during metadata extraction."""

    tracks: list[TrackMetadata] = field(default_factory=list)
    skipped_by_reason: dict[SkipReason, int] = field(default_factory=dict)
    unavailable_tracks: list[UnavailableTrack] = field(default_factory=list)
    playlist_total: int = 0
    playlist_kind: str | None = None
    playlist_title: str | None = None

    @property
    def skipped(self) -> int:
        """Total skipped tracks."""
        return sum(self.skipped_by_reason.values())

    @property
    def unavailable(self) -> int:
        """Tracks without video ID."""
        return self.skipped_by_reason.get(SkipReason.NO_VIDEO_ID, 0)

    def update_from_progress(self, progress: ExtractProgress) -> None:
        """Update state from extraction progress."""
        if progress.track is not None:
            self.tracks.append(progress.track)
        self.skipped_by_reason = progress.skipped_by_reason
        self.unavailable_tracks = list(progress.playlist_info.unavailable_tracks)
        self.playlist_total = progress.playlist_total
        self.playlist_kind = progress.playlist_info.kind.value
        self.playlist_title = progress.playlist_info.title
