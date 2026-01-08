"""Shared type definitions for the application."""

from collections.abc import Callable
from datetime import datetime
from typing import Literal

# Supported audio formats for yt-dlp downloads
type AudioFormat = Literal["opus", "mp3", "m4a", "aac", "flac", "wav", "vorbis"]

# Audio file extensions (includes vorbis as .ogg, weba for WebM audio)
AUDIO_EXTENSIONS = frozenset({
    ".opus",
    ".mp3",
    ".m4a",
    ".aac",
    ".flac",
    ".wav",
    ".ogg",
    ".weba",
})

# Log status values (matches ProgressStep enum values)
type LogStatus = Literal[
    "fetching_info",
    "downloading",
    "importing",
    "completed",
    "failed",
    "cancelled",
]

# Callable type aliases for dependency injection
type Clock = Callable[[], datetime]
type IdGenerator = Callable[[], str]
