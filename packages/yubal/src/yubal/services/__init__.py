"""Business logic services for yubal.

Public API:
    MetadataExtractorService - Extract metadata from YouTube Music playlists
    PlaylistDownloadService - Full pipeline: extract + download + compose
    ArtistDiscographyService - Search artists and list their releases

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

from yubal.services.artist_service import ArtistDiscographyService
from yubal.services.extractor import MetadataExtractorService
from yubal.services.playlist_download_service import PlaylistDownloadService

__all__ = [
    "ArtistDiscographyService",
    "MetadataExtractorService",
    "PlaylistDownloadService",
]
