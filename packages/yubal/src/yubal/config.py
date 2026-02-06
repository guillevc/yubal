"""Configuration for yubal."""

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
        fetch_lyrics: Whether to fetch lyrics from lrclib.net.
    """

    base_path: Path
    codec: AudioCodec = AudioCodec.OPUS
    quality: int = 0
    quiet: bool = True
    fetch_lyrics: bool = True


@dataclass(frozen=True)
class PlaylistDownloadConfig:
    """Playlist download service configuration.

    Combines download settings with playlist-specific options.

    Attributes:
        download: Download configuration for tracks.
        generate_m3u: Whether to generate M3U playlist file.
        save_cover: Whether to save playlist cover image.
        skip_album_m3u: Skip M3U generation for album playlists.
        max_items: Maximum number of tracks to download.
        apply_replaygain: Whether to apply ReplayGain tags using rsgain.
    """

    download: DownloadConfig
    generate_m3u: bool = True
    save_cover: bool = True
    skip_album_m3u: bool = True
    max_items: int | None = None
    apply_replaygain: bool = True
