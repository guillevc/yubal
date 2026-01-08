"""YouTube Music downloader using yt-dlp Python API."""

import contextlib
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import yt_dlp
from loguru import logger
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.postprocessor.metadataparser import MetadataParserPP
from yt_dlp.utils import DownloadCancelled

from yubal.core.callbacks import CancelCheck, ProgressCallback, ProgressEvent
from yubal.core.enums import ProgressStep
from yubal.core.models import AlbumInfo, DownloadResult
from yubal.core.types import AUDIO_EXTENSIONS


class FileCollectorPP(PostProcessor):
    """Custom PostProcessor that captures final audio file paths.

    This PP runs at the end of the postprocessor chain to capture the
    final filepath after all conversions (FFmpegExtractAudio, etc.).

    The postprocessor hook approach doesn't work reliably because hooks
    are called after EACH postprocessor, and the filepath in info_dict
    may still point to intermediate files (e.g., .webm before extraction).
    """

    def __init__(
        self,
        downloader: yt_dlp.YoutubeDL | None = None,
        collected_files: set[Path] | None = None,
    ):
        super().__init__(downloader)
        self.collected_files = collected_files if collected_files is not None else set()

    def run(self, info):  # type: ignore[override]
        """Capture the final filepath after all postprocessing."""
        filepath = info.get("filepath")
        if filepath:
            path = Path(filepath)
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                self.collected_files.add(path)
                logger.debug("Collected final audio file: {}", path.name)
            else:
                logger.debug("Ignoring non-audio file in collector: {}", path.name)
        return [], info


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

# YouTube video ID pattern: 11 characters, alphanumeric + hyphen + underscore
_VIDEO_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{11}$")


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

    def _make_progress_hook(
        self,
        track_num: int,
        total_tracks: int | None,
        progress_callback: ProgressCallback | None,
        cancel_check: CancelCheck | None,
    ) -> Callable[[dict[str, Any]], None]:
        """Create a progress hook for download progress.

        Args:
            track_num: Current track number (1-based)
            total_tracks: Total tracks if known, None for playlist downloads
            progress_callback: Optional callback for progress updates
            cancel_check: Function returning True if download should cancel
        """

        def hook(d: dict[str, Any]) -> None:
            if cancel_check and cancel_check():
                raise DownloadCancelled("Download cancelled by user")

            # For playlist downloads, get track from info_dict; for single use param
            if total_tracks is None:
                info = d.get("info_dict", {})
                current_track = info.get("playlist_index") or 1
                track_label = f"Track {current_track}"
            else:
                current_track = track_num
                track_label = f"Track {track_num}/{total_tracks}"

            track_idx = current_track - 1  # 0-based for details

            if d["status"] == "downloading":
                percent_str = d.get("_percent_str", "").strip()
                speed = d.get("_speed_str", "").strip()
                percent_value: float | None = None
                if percent_str:
                    with contextlib.suppress(ValueError):
                        percent_value = float(percent_str.rstrip("%"))

                if progress_callback and percent_value is not None:
                    progress_callback(
                        ProgressEvent(
                            step=ProgressStep.DOWNLOADING,
                            message=f"{track_label}: {percent_str} at {speed}",
                            progress=percent_value,
                            details={"speed": speed, "track_index": track_idx},
                        )
                    )
                elif percent_str:
                    logger.debug("{}: {} at {}", track_label, percent_str, speed)

            elif d["status"] == "finished":
                if progress_callback:
                    progress_callback(
                        ProgressEvent(
                            step=ProgressStep.DOWNLOADING,
                            message=f"{track_label} complete",
                            progress=100.0,
                            details={"track_index": track_idx},
                        )
                    )

        return hook

    def _create_progress_hook(
        self,
        progress_callback: ProgressCallback | None = None,
        cancel_check: CancelCheck | None = None,
    ) -> Callable[[dict[str, Any]], None]:
        """Create a progress hook for playlist/album downloads."""
        return self._make_progress_hook(
            track_num=1,
            total_tracks=None,  # Will read from playlist_index
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )

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
            # Create file collector PP to capture final audio paths
            # This runs at the end of all postprocessors, after FFmpegExtractAudio
            # has converted the file to the target format (.mp3, etc.)
            file_collector = FileCollectorPP(collected_files=downloaded_files)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Add our collector at the end of the post_process chain
                ydl.add_post_processor(file_collector, when="post_process")
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

    def download_tracks(
        self,
        video_ids: Sequence[str],
        output_dir: Path,
        progress_callback: ProgressCallback | None = None,
        cancel_check: CancelCheck | None = None,
    ) -> DownloadResult:
        """Download specific tracks by video ID.

        Downloads tracks individually to guarantee ordering matches the input
        video_ids sequence. This is essential for playlists where ytmusicapi
        metadata must align 1:1 with downloaded files.

        Args:
            video_ids: Video IDs to download, in order
            output_dir: Directory to save downloaded files
            progress_callback: Optional callback for progress updates
            cancel_check: Function returning True if download should cancel

        Returns:
            DownloadResult with files in same order as video_ids.
            success=True only if all tracks downloaded successfully.
        """
        output_dir.mkdir(parents=True, exist_ok=True)

        downloaded_files: list[Path] = []
        skipped_ids: list[str] = []
        total_tracks = len(video_ids)

        for track_num, video_id in enumerate(video_ids, start=1):
            if cancel_check and cancel_check():
                return DownloadResult(
                    success=False,
                    output_dir=str(output_dir),
                    downloaded_files=[str(f) for f in downloaded_files],
                    error="Download cancelled",
                    cancelled=True,
                )

            # Validate video ID format
            if not _VIDEO_ID_PATTERN.match(video_id):
                logger.warning("Invalid video ID format, skipping: {}", video_id)
                skipped_ids.append(video_id)
                continue

            url = f"https://www.youtube.com/watch?v={video_id}"
            track_files: set[Path] = set()

            progress_hook = self._make_progress_hook(
                track_num=track_num,
                total_tracks=total_tracks,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )

            ydl_opts = self._get_track_ydl_opts(output_dir, track_num, progress_hook)

            try:
                file_collector = FileCollectorPP(collected_files=track_files)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.add_post_processor(file_collector, when="post_process")
                    ydl.extract_info(url, download=True)

                # Handle collected files - expect exactly one per track
                if len(track_files) == 0:
                    logger.warning("No file collected for track {}", video_id)
                    skipped_ids.append(video_id)
                elif len(track_files) > 1:
                    logger.warning(
                        "Multiple files for track {}: {}, using first",
                        video_id,
                        [f.name for f in track_files],
                    )
                    # Sort to get deterministic ordering if multiple files
                    downloaded_files.append(min(track_files))
                else:
                    downloaded_files.append(next(iter(track_files)))

            except DownloadCancelled:
                return DownloadResult(
                    success=False,
                    output_dir=str(output_dir),
                    downloaded_files=[str(f) for f in downloaded_files],
                    error="Download cancelled",
                    cancelled=True,
                )
            except yt_dlp.DownloadError as e:
                logger.warning("Failed to download track {}: {}", video_id, e)
                skipped_ids.append(video_id)
                # Continue with other tracks (ignoreerrors behavior)

        # Success only if all tracks downloaded
        all_downloaded = len(downloaded_files) == total_tracks
        if skipped_ids:
            error_msg = f"Failed to download {len(skipped_ids)} tracks: {skipped_ids}"
        else:
            error_msg = None

        return DownloadResult(
            success=all_downloaded,
            output_dir=str(output_dir),
            downloaded_files=[str(f) for f in downloaded_files],
            error=error_msg,
        )

    def _get_track_ydl_opts(
        self,
        output_dir: Path,
        track_num: int,
        progress_hook: Callable[[dict[str, Any]], None],
    ) -> dict[str, Any]:
        """Build yt-dlp options for single track download with explicit track number."""
        postprocessors: list[dict[str, Any]] = []

        if self.audio_format != "best":
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": self.audio_format,
                "preferredquality": self.audio_quality,
            })

        postprocessors.extend([
            {"key": "FFmpegMetadata", "add_metadata": True},
            {"key": "EmbedThumbnail"},
        ])

        ydl_opts: dict[str, Any] = {
            "format": "bestaudio/best",
            # Use explicit track number instead of playlist_index
            "outtmpl": str(output_dir / f"{track_num:02d} - %(title)s.%(ext)s"),
            "postprocessors": postprocessors,
            "writethumbnail": True,
            "progress_hooks": [progress_hook],
            "logger": YtdlpLogger(),
        }

        if self.cookies_file and self.cookies_file.exists():
            ydl_opts["cookiefile"] = str(self.cookies_file)

        return ydl_opts

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
            first_entry = entries[0] if entries else None

            # For album artist: try playlist-level artists, then first entry's artist
            album_artist = _eval("%(artists.0,channel,uploader|)s", info)
            if not album_artist and first_entry:
                album_artist = _eval(
                    "%(artists.0,artist,uploader|Unknown)s", first_entry
                )
            album_artist = album_artist or "Unknown"

            # For album title: try first track's album field, then playlist title
            # Note: correct album name will be read from file metadata after download
            album_title = _eval("%(album|)s", first_entry) if first_entry else ""
            if not album_title:
                album_title = _eval("%(title|Unknown Album)s", info)

            # Prefer first track's data over playlist-level data
            year = None
            thumbnail_url = None
            audio_codec = None
            audio_bitrate = None
            if first_entry:
                year = self._extract_year(first_entry)
                thumbnail_url = self._extract_thumbnail(first_entry)
                audio_codec, audio_bitrate = self._extract_audio_info(first_entry)
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
            postprocessors.append({
                "key": "FFmpegExtractAudio",
                "preferredcodec": self.audio_format,
                "preferredquality": self.audio_quality,
            })

        # Add metadata and thumbnail postprocessors
        postprocessors.extend([
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
        ])

        ydl_opts: dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": str(output_dir / "%(playlist_index|0)02d - %(title)s.%(ext)s"),
            "postprocessors": postprocessors,
            "writethumbnail": True,  # Download thumbnail for EmbedThumbnail PP
            "progress_hooks": [progress_hook],
            "ignoreerrors": True,  # Continue on individual track errors
            "logger": YtdlpLogger(),
        }

        # Use cookies if available (for Premium quality, bypassing rate limits, etc.)
        if self.cookies_file and self.cookies_file.exists():
            ydl_opts["cookiefile"] = str(self.cookies_file)

        return ydl_opts
