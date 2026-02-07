"""Business logic services for yubal.

Public API:
    MetadataExtractorService - Extract metadata from YouTube Music playlists
    PlaylistDownloadService - Full pipeline: extract + download + compose

Protocols (for dependency injection):
    ReplayGainProtocol - ReplayGain tagging abstraction
    PlaylistArtifactsProtocol - Playlist artifact generation abstraction
    DownloaderProtocol - Download backend abstraction
    LyricsServiceProtocol - Lyrics fetching abstraction

Internal (not exported):
    DownloadService, PlaylistArtifactsService - Used internally
    ReplayGainService - rsgain-based ReplayGain implementation
    YTDLPDownloader - yt-dlp download backend implementation
    LyricsService - lrclib.net lyrics fetching
    AudioFileTaggingService, tag_track - Audio file tagging
"""

from yubal.services.extractor import MetadataExtractorService
from yubal.services.pipeline import PlaylistDownloadService

__all__ = [
    "MetadataExtractorService",
    "PlaylistDownloadService",
]
