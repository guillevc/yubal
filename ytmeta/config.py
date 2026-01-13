"""Configuration for ytmeta."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class AudioCodec(StrEnum):
    """Supported audio output codecs."""

    OPUS = "opus"
    MP3 = "mp3"
    M4A = "m4a"


@dataclass(frozen=True)
class APIConfig:
    """YouTube Music API configuration.

    Attributes:
        search_limit: Maximum number of search results to return.
        ignore_spelling: Whether to ignore spelling in search queries.
    """

    search_limit: int = 1
    ignore_spelling: bool = True


@dataclass(frozen=True)
class DownloadConfig:
    """Download service configuration.

    Attributes:
        base_path: Base directory for downloaded files.
        codec: Audio codec for output files.
        quality: Audio quality (0 = best, 10 = worst). Only applies to lossy codecs.
        quiet: Suppress yt-dlp output.
    """

    base_path: Path
    codec: AudioCodec = AudioCodec.OPUS
    quality: int = 0
    quiet: bool = True
