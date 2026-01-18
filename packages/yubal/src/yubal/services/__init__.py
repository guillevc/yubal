"""Business logic services for yubal.

Public API:
    MetadataExtractorService - Extract metadata from YouTube Music playlists
    PlaylistDownloadService - Full pipeline: extract + download + compose

Internal (not exported):
    DownloadService, PlaylistComposerService - Used internally
    DownloaderProtocol, YTDLPDownloader - Download backend implementation
    tag_track - Audio file tagging
"""

from yubal.services.extractor import MetadataExtractorService
from yubal.services.playlist import PlaylistDownloadService

__all__ = [
    "MetadataExtractorService",
    "PlaylistDownloadService",
]
