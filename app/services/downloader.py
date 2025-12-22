"""YouTube Music downloader using yt-dlp Python API."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yt_dlp
from yt_dlp.postprocessor.metadataparser import MetadataParserPP


@dataclass
class TrackInfo:
    """Information about a single track."""

    title: str
    artist: str
    track_number: int
    duration: int  # seconds
    filename: Optional[str] = None


@dataclass
class AlbumInfo:
    """Information about an album/playlist."""

    title: str
    artist: str
    year: Optional[int]
    track_count: int
    tracks: list[TrackInfo] = field(default_factory=list)
    playlist_id: str = ""
    url: str = ""


@dataclass
class DownloadResult:
    """Result of a download operation."""

    success: bool
    album_info: Optional[AlbumInfo]
    output_dir: Path
    downloaded_files: list[Path] = field(default_factory=list)
    error: Optional[str] = None


class Downloader:
    """Handles YouTube Music album downloads via yt-dlp."""

    def __init__(self, audio_format: str = "mp3", audio_quality: str = "0"):
        self.audio_format = audio_format
        self.audio_quality = audio_quality

    def extract_info(self, url: str) -> AlbumInfo:
        """
        Extract album/playlist metadata without downloading.

        Args:
            url: YouTube Music playlist URL

        Returns:
            AlbumInfo with album and track metadata

        Raises:
            ValueError: If URL is not a valid playlist
            yt_dlp.DownloadError: If extraction fails
        """
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            if not info:
                raise ValueError("Could not extract info from URL")

            # Handle playlist vs single video
            if "entries" in info:
                entries = list(info.get("entries", []))
                tracks = []
                for i, entry in enumerate(entries, 1):
                    if entry:
                        tracks.append(
                            TrackInfo(
                                title=entry.get("title", f"Track {i}"),
                                artist=entry.get("artist", entry.get("uploader", "Unknown")),
                                track_number=i,
                                duration=entry.get("duration", 0),
                            )
                        )

                return AlbumInfo(
                    title=info.get("title", "Unknown Album"),
                    artist=info.get("uploader", info.get("channel", "Unknown Artist")),
                    year=self._extract_year(info),
                    track_count=len(tracks),
                    tracks=tracks,
                    playlist_id=info.get("id", ""),
                    url=url,
                )
            else:
                # Single track
                return AlbumInfo(
                    title=info.get("album", info.get("title", "Unknown")),
                    artist=info.get("artist", info.get("uploader", "Unknown")),
                    year=self._extract_year(info),
                    track_count=1,
                    tracks=[
                        TrackInfo(
                            title=info.get("title", "Unknown"),
                            artist=info.get("artist", "Unknown"),
                            track_number=1,
                            duration=info.get("duration", 0),
                        )
                    ],
                    playlist_id=info.get("id", ""),
                    url=url,
                )

    def _extract_year(self, info: dict) -> Optional[int]:
        """Extract year from upload_date or release_year."""
        if info.get("release_year"):
            return info["release_year"]
        upload_date = info.get("upload_date", "")
        if upload_date and len(upload_date) >= 4:
            try:
                return int(upload_date[:4])
            except ValueError:
                pass
        return None

    def download_album(self, url: str, output_dir: Path) -> DownloadResult:
        """
        Download all tracks from a YouTube Music album.

        Args:
            url: YouTube Music playlist URL
            output_dir: Directory to save downloaded files

        Returns:
            DownloadResult with success status and file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        downloaded_files: list[Path] = []
        album_info: Optional[AlbumInfo] = None

        def progress_hook(d):
            if d["status"] == "downloading":
                # Print download progress
                percent = d.get("_percent_str", "").strip()
                speed = d.get("_speed_str", "").strip()
                if percent:
                    print(f"\r  Downloading: {percent} at {speed}", end="", flush=True)
            elif d["status"] == "finished":
                print()  # New line after progress
                filename = d.get("info_dict", {}).get("filepath") or d.get("filename")
                if filename:
                    downloaded_files.append(Path(filename))
                    print(f"  Completed: {Path(filename).name}")

        ydl_opts = self._get_ydl_opts(output_dir, progress_hook)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                album_info = self._parse_album_info(info, url)

            # Find all audio files in output directory
            audio_extensions = {".mp3", ".m4a", ".opus", ".ogg", ".flac", ".wav"}
            all_files = [
                f for f in output_dir.iterdir()
                if f.is_file() and f.suffix.lower() in audio_extensions
            ]

            return DownloadResult(
                success=True,
                album_info=album_info,
                output_dir=output_dir,
                downloaded_files=all_files,
            )

        except yt_dlp.DownloadError as e:
            return DownloadResult(
                success=False,
                album_info=album_info,
                output_dir=output_dir,
                downloaded_files=[],
                error=str(e),
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                album_info=album_info,
                output_dir=output_dir,
                downloaded_files=[],
                error=f"Unexpected error: {str(e)}",
            )

    def _parse_album_info(self, info: dict, url: str) -> AlbumInfo:
        """Parse album info from yt-dlp extraction result."""
        if not info:
            return AlbumInfo(
                title="Unknown",
                artist="Unknown",
                year=None,
                track_count=0,
                url=url,
            )

        if "entries" in info:
            entries = list(info.get("entries", []))
            tracks = []
            for i, entry in enumerate(entries, 1):
                if entry:
                    tracks.append(
                        TrackInfo(
                            title=entry.get("title", f"Track {i}"),
                            artist=entry.get("artist", entry.get("uploader", "Unknown")),
                            track_number=i,
                            duration=entry.get("duration", 0),
                        )
                    )

            return AlbumInfo(
                title=info.get("title", "Unknown Album"),
                artist=info.get("uploader", info.get("channel", "Unknown")),
                year=self._extract_year(info),
                track_count=len(tracks),
                tracks=tracks,
                playlist_id=info.get("id", ""),
                url=url,
            )

        return AlbumInfo(
            title=info.get("album", info.get("title", "Unknown")),
            artist=info.get("artist", info.get("uploader", "Unknown")),
            year=self._extract_year(info),
            track_count=1,
            playlist_id=info.get("id", ""),
            url=url,
        )

    def _get_ydl_opts(self, output_dir: Path, progress_hook) -> dict:
        """Build yt-dlp options dictionary."""
        return {
            "format": "bestaudio/best",
            "remote_components": ["ejs:github"],
            "outtmpl": str(output_dir / "%(playlist_index|0)02d - %(title)s.%(ext)s"),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self.audio_format,
                    "preferredquality": self.audio_quality,
                },
                # Set track number from playlist index, and use release_date instead of upload_date
                {
                    "key": "MetadataParser",
                    "when": "pre_process",
                    "actions": [
                        (MetadataParserPP.Actions.INTERPRET, "playlist_index", "%(meta_track)s"),
                        (MetadataParserPP.Actions.INTERPRET, "release_date", "%(meta_date)s"),
                        (MetadataParserPP.Actions.INTERPRET, "artist", "%(meta_album_artist)s"),
                    ],
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
                {
                    "key": "EmbedThumbnail",
                },
                # Remove unwanted YouTube metadata tags (runs after EmbedThumbnail)
                {
                    "key": "Exec",
                    "exec_cmd": 'ffmpeg -y -i %(filepath)q -c copy -metadata genre= -metadata comment= -metadata purl= -metadata description= -metadata synopsis= -f mp3 %(filepath)q.tmp && mv %(filepath)q.tmp %(filepath)q',
                },
            ],
            "writethumbnail": True,
            "progress_hooks": [progress_hook],
            "ignoreerrors": True,  # Continue on individual track errors
            "no_warnings": False,
            "quiet": False,
        }
