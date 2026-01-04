"""YouTube Music downloader using yt-dlp Python API."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yt_dlp
from loguru import logger
from yt_dlp.postprocessor.metadataparser import MetadataParserPP
from yt_dlp.utils import DownloadCancelled

from yubal.core.callbacks import CancelCheck, ProgressCallback, ProgressEvent
from yubal.core.enums import ProgressStep
from yubal.core.models import AlbumInfo, DownloadResult


class YtdlpLogger:
    """Custom logger for yt-dlp that uses loguru."""

    def debug(self, msg: str) -> None:
        # yt-dlp sends most output as debug, filter noise
        if msg.startswith("[debug]"):
            return
        logger.debug("[yt-dlp] {}", msg)

    def info(self, msg: str) -> None:
        logger.info("[yt-dlp] {}", msg)

    def warning(self, msg: str) -> None:
        logger.warning("[yt-dlp] {}", msg)

    def error(self, msg: str) -> None:
        logger.error("[yt-dlp] {}", msg)


# Shared yt-dlp instance for template evaluation
_ydl = yt_dlp.YoutubeDL({"quiet": True})


def _eval(template: str, info: dict[str, Any]) -> str:
    """Evaluate yt-dlp template with fallback support."""
    return _ydl.evaluate_outtmpl(template, info)


class Downloader:
    """Handles YouTube Music album downloads via yt-dlp."""

    def __init__(
        self,
        audio_format: str = "mp3",
        audio_quality: str = "0",
        cookies_file: Path | None = None,
    ):
        self.audio_format = audio_format
        self.audio_quality = audio_quality
        self.cookies_file = cookies_file

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
            "extract_flat": False,  # Full extraction to get year/album/codec
            "playlist_items": "1",  # Only extract first item (still get playlist_count)
            # Explicitly disable cookies for info extraction to avoid bot detection.
            # Cookies can trigger YouTube's anti-bot measures during metadata fetch.
            "cookiefile": None,
            "cookiesfrombrowser": None,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("Could not extract info from URL")
            return self._parse_album_info(info, url)

    def _extract_year(self, info: dict[str, Any]) -> int | None:
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

    def _extract_thumbnail(self, info: dict[str, Any]) -> str | None:
        """Extract best thumbnail URL from info."""
        # Try direct thumbnail field first
        if info.get("thumbnail"):
            return info["thumbnail"]

        # Try thumbnails array - prefer larger ones
        thumbnails = info.get("thumbnails", [])
        if thumbnails:
            # Sort by preference (width if available, otherwise last in list)
            best = max(
                thumbnails,
                key=lambda t: t.get("width", 0) or t.get("preference", 0),
            )
            return best.get("url")

        return None

    def _create_progress_hook(
        self,
        progress_callback: ProgressCallback | None = None,
        cancel_check: CancelCheck | None = None,
    ) -> Callable[[dict[str, Any]], None]:
        """Create a progress hook for download progress (percent, speed)."""

        def hook(d: dict[str, Any]) -> None:
            # Check for cancellation before processing
            if cancel_check and cancel_check():
                raise DownloadCancelled("Download cancelled by user")

            # Get track index from playlist_index in info_dict.
            # For single videos (not playlists), playlist_index is None,
            # so we default to track 0.
            info = d.get("info_dict", {})
            track_idx = (info.get("playlist_index") or 1) - 1  # 0-based

            if d["status"] == "downloading":
                percent_str = d.get("_percent_str", "").strip()
                speed = d.get("_speed_str", "").strip()
                # Parse percentage for callback
                percent_value: float | None = None
                if percent_str:
                    try:
                        percent_value = float(percent_str.rstrip("%"))
                    except ValueError:
                        pass

                if progress_callback and percent_value is not None:
                    progress_callback(
                        ProgressEvent(
                            step=ProgressStep.DOWNLOADING,
                            message=f"Track {track_idx + 1}: {percent_str} at {speed}",
                            progress=percent_value,
                            details={"speed": speed, "track_index": track_idx},
                        )
                    )
                elif percent_str:
                    logger.debug(
                        "Track {}: {} at {}", track_idx + 1, percent_str, speed
                    )
            elif d["status"] == "finished":
                if progress_callback:
                    progress_callback(
                        ProgressEvent(
                            step=ProgressStep.DOWNLOADING,
                            message=f"Track {track_idx + 1} download complete",
                            progress=100.0,
                            details={"track_index": track_idx},
                        )
                    )

        return hook

    def _create_postprocessor_hook(
        self,
        downloaded_files: set[Path],
    ) -> Callable[[dict[str, Any]], None]:
        """Capture filepaths from postprocessors, dedupe with set."""

        def hook(d: dict[str, Any]) -> None:
            if d["status"] != "finished":
                return

            filepath = d.get("info_dict", {}).get("filepath")
            if filepath:
                downloaded_files.add(Path(filepath))

        return hook

    def download_album(
        self,
        url: str,
        output_dir: Path,
        progress_callback: ProgressCallback | None = None,
        cancel_check: CancelCheck | None = None,
    ) -> DownloadResult:
        """
        Download all tracks from a YouTube Music album.

        Args:
            url: YouTube Music playlist URL
            output_dir: Directory to save downloaded files
            progress_callback: Optional callback for progress updates
            cancel_check: Function returning True if download should cancel

        Returns:
            DownloadResult with success status and file paths
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        downloaded_files: set[Path] = set()
        album_info: AlbumInfo | None = None

        ydl_opts = self._get_ydl_opts(
            output_dir,
            self._create_progress_hook(progress_callback, cancel_check),
        )

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Bug workaround: must call add_postprocessor_hook() explicitly
                # See: https://github.com/yt-dlp/yt-dlp/issues/1650
                ydl.add_postprocessor_hook(
                    self._create_postprocessor_hook(downloaded_files)
                )
                info = ydl.extract_info(url, download=True)
                album_info = self._parse_album_info(info, url)

            return DownloadResult(
                success=True,
                album_info=album_info,
                output_dir=str(output_dir),
                downloaded_files=[str(f) for f in downloaded_files],
            )

        except DownloadCancelled:
            return DownloadResult(
                success=False,
                album_info=album_info,
                output_dir=str(output_dir),
                error="Download cancelled",
                cancelled=True,
            )
        except yt_dlp.DownloadError as e:
            return DownloadResult(
                success=False,
                album_info=album_info,
                output_dir=str(output_dir),
                error=str(e),
            )
        except Exception as e:
            return DownloadResult(
                success=False,
                album_info=album_info,
                output_dir=str(output_dir),
                error=f"Unexpected error: {e!s}",
            )

    def _extract_audio_info(
        self, info: dict[str, Any]
    ) -> tuple[str | None, int | None]:
        """Extract audio codec and bitrate from yt-dlp info dict.

        Returns the target format (what user gets), not necessarily the source.
        """
        # Use configured format, fall back to source codec for "best"
        if self.audio_format != "best":
            audio_codec = self.audio_format
        else:
            audio_codec = info.get("acodec")

        # Bitrate from source (close enough for display purposes)
        abr = info.get("abr")
        audio_bitrate = int(abr) if abr else None

        return audio_codec, audio_bitrate

    def _parse_album_info(self, info: dict[str, Any], url: str) -> AlbumInfo:
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

            # For album artist: try playlist-level artists, then first entry's artist
            album_artist = _eval("%(artists.0,channel,uploader|)s", info)
            if not album_artist and entries:
                # Fall back to first track's artist
                first_entry = entries[0]
                if first_entry:
                    album_artist = _eval(
                        "%(artists.0,artist,uploader|Unknown)s", first_entry
                    )
            album_artist = album_artist or "Unknown"

            # For album title: try first track's album field, then playlist title
            # Note: correct album name will be read from file metadata after download
            album_title = ""
            if entries:
                first_entry = entries[0]
                if first_entry:
                    album_title = _eval("%(album|)s", first_entry)
            if not album_title:
                album_title = _eval("%(title|Unknown Album)s", info)

            # Prefer first track's data over playlist-level data
            year = None
            thumbnail_url = None
            audio_codec = None
            audio_bitrate = None
            if entries and entries[0]:
                year = self._extract_year(entries[0])
                thumbnail_url = self._extract_thumbnail(entries[0])
                audio_codec, audio_bitrate = self._extract_audio_info(entries[0])
            if not year:
                year = self._extract_year(info)
            if not thumbnail_url:
                thumbnail_url = self._extract_thumbnail(info)

            return AlbumInfo(
                title=album_title,
                artist=album_artist,
                year=year,
                track_count=info.get("playlist_count") or len(entries),
                playlist_id=_eval("%(id|)s", info),
                url=url,
                thumbnail_url=thumbnail_url,
                audio_codec=audio_codec,
                audio_bitrate=audio_bitrate,
            )

        # Single track
        audio_codec, audio_bitrate = self._extract_audio_info(info)
        return AlbumInfo(
            title=_eval("%(album,title|Unknown)s", info),
            artist=_eval("%(artists.0,artist,uploader|Unknown)s", info),
            year=self._extract_year(info),
            track_count=1,
            playlist_id=_eval("%(id|)s", info),
            url=url,
            thumbnail_url=self._extract_thumbnail(info),
            audio_codec=audio_codec,
            audio_bitrate=audio_bitrate,
        )

    def _get_ydl_opts(
        self, output_dir: Path, progress_hook: Callable[[dict[str, Any]], None]
    ) -> dict[str, Any]:
        """Build yt-dlp options dictionary."""
        postprocessors: list[dict[str, Any]] = []

        # Only add FFmpegExtractAudio when format conversion needed
        # When source matches target (e.g. opus→opus), FFmpeg uses -acodec copy (fast)
        # When "best", keep original format without any processing
        if self.audio_format != "best":
            postprocessors.append(
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self.audio_format,
                    "preferredquality": self.audio_quality,
                }
            )

        # Add metadata and thumbnail postprocessors
        postprocessors.extend(
            [
                # Set track number from playlist index, use release_date
                {
                    "key": "MetadataParser",
                    "when": "pre_process",
                    "actions": [
                        (
                            MetadataParserPP.Actions.INTERPRET,
                            "playlist_index",
                            "%(meta_track)s",
                        ),
                        (
                            MetadataParserPP.Actions.INTERPRET,
                            "release_date",
                            "%(meta_date)s",
                        ),
                        (
                            MetadataParserPP.Actions.INTERPRET,
                            "%(artists.0)s",
                            "%(meta_artist)s",
                        ),
                    ],
                },
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
                {
                    "key": "EmbedThumbnail",
                },
            ]
        )

        ydl_opts: dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": str(output_dir / "%(playlist_index|0)02d - %(title)s.%(ext)s"),
            "postprocessors": postprocessors,
            "writethumbnail": True,
            "progress_hooks": [progress_hook],
            "ignoreerrors": True,  # Continue on individual track errors
            "logger": YtdlpLogger(),
        }

        # Use cookies if available (for Premium quality, bypassing rate limits, etc.)
        if self.cookies_file and self.cookies_file.exists():
            ydl_opts["cookiefile"] = str(self.cookies_file)

        return ydl_opts
