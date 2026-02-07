"""Enumerations for yubal domain models."""

from enum import StrEnum


class VideoType(StrEnum):
    """YouTube Music video types.

    Maps to ytmusicapi.models.content.enums.VideoType values.
    """

    ATV = "MUSIC_VIDEO_TYPE_ATV"  # Audio Track Video (album version)
    OMV = "MUSIC_VIDEO_TYPE_OMV"  # Official Music Video
    OFFICIAL_SOURCE_MUSIC = "MUSIC_VIDEO_TYPE_OFFICIAL_SOURCE_MUSIC"  # Official source
    UGC = "MUSIC_VIDEO_TYPE_UGC"  # User Generated Content


class DownloadStatus(StrEnum):
    """Status of a download operation."""

    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"


class SkipReason(StrEnum):
    """Reason why a track was skipped.

    Used in both extraction and download phases:
    - Extraction: UNSUPPORTED_VIDEO_TYPE, NO_VIDEO_ID, REGION_UNAVAILABLE
    - Download: FILE_EXISTS
    """

    FILE_EXISTS = "file_exists"
    UNSUPPORTED_VIDEO_TYPE = "unsupported_video_type"
    NO_VIDEO_ID = "no_video_id"
    REGION_UNAVAILABLE = "region_unavailable"

    @property
    def label(self) -> str:
        """Human-readable label for display."""
        match self:
            case SkipReason.FILE_EXISTS:
                return "file exists"
            case SkipReason.UNSUPPORTED_VIDEO_TYPE:
                return "unsupported video type"
            case SkipReason.NO_VIDEO_ID:
                return "no video ID"
            case SkipReason.REGION_UNAVAILABLE:
                return "region unavailable"


class ContentKind(StrEnum):
    """Type of music content (album vs playlist vs track)."""

    ALBUM = "album"
    PLAYLIST = "playlist"
    TRACK = "track"
