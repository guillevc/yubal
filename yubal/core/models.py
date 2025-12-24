"""Domain models shared across CLI and API."""

from pydantic import BaseModel


class TrackInfo(BaseModel):
    """Information about a single track."""

    title: str
    artist: str
    track_number: int
    duration: int  # seconds
    filename: str | None = None


class AlbumInfo(BaseModel):
    """Information about an album/playlist."""

    title: str
    artist: str
    year: int | None = None
    track_count: int
    tracks: list[TrackInfo] = []
    playlist_id: str = ""
    url: str = ""


class DownloadResult(BaseModel):
    """Result of a download operation."""

    success: bool
    album_info: AlbumInfo | None = None
    output_dir: str
    downloaded_files: list[str] = []
    error: str | None = None


class TagResult(BaseModel):
    """Result of a tagging operation."""

    success: bool
    source_dir: str
    dest_dir: str | None = None
    album_name: str | None = None
    artist_name: str | None = None
    track_count: int = 0
    error: str | None = None


class LibraryHealth(BaseModel):
    """Result of a library health check."""

    healthy: bool
    library_album_count: int
    database_album_count: int
    message: str


class SyncResult(BaseModel):
    """Result of a sync operation."""

    success: bool
    download_result: DownloadResult | None = None
    tag_result: TagResult | None = None
    album_info: AlbumInfo | None = None
    destination: str | None = None
    error: str | None = None
