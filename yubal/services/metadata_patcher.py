"""Audio file metadata patching via mutagen.

Patches downloaded audio files with enriched metadata from ytmusicapi,
overwriting the raw metadata that yt-dlp embeds.
"""

import base64
from collections.abc import Sequence
from pathlib import Path

import httpx
from loguru import logger
from mutagen import File as MutagenFile
from mutagen.flac import Picture
from mutagen.id3 import APIC, ID3
from mutagen.mp4 import MP4Cover
from mutagen.oggopus import OggOpus
from mutagen.oggvorbis import OggVorbis

from yubal.services.metadata_enricher import TrackMetadata


class MetadataPatcher:
    """Patches audio file metadata with enriched values."""

    def __init__(self, http_timeout: float = 10.0):
        """Initialize the patcher with an HTTP client for artwork downloads."""
        self._http_client: httpx.Client | None = None
        self._http_timeout = http_timeout

    def _get_http_client(self) -> httpx.Client:
        """Get or create the HTTP client for artwork downloads."""
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=self._http_timeout)
        return self._http_client

    def close(self) -> None:
        """Close the HTTP client. Call when done with the patcher."""
        if self._http_client is not None:
            self._http_client.close()
            self._http_client = None

    def __enter__(self) -> "MetadataPatcher":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _detect_mime_type(self, data: bytes) -> str:
        """Detect image format from magic bytes."""
        if data[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        return "image/jpeg"

    def _force_jpeg_url(self, url: str) -> str:
        """Request JPEG format from Google's image servers."""
        if not url:
            return url
        if "googleusercontent.com" in url or "ytimg.com" in url:
            return f"{url.split('=', maxsplit=1)[0]}=s544-rj"
        return url

    def _get_jpeg_dimensions(self, data: bytes) -> tuple[int, int]:
        """Extract width/height from JPEG SOF marker.

        Parses SOF0 (baseline) or SOF2 (progressive) markers.
        Returns (width, height) or (0, 0) if parsing fails.
        """
        if len(data) < 11 or data[:2] != b"\xff\xd8":
            return (0, 0)

        pos = 2
        while pos < len(data) - 9:
            if data[pos] != 0xFF:
                pos += 1
                continue

            marker = data[pos + 1]

            # SOF0 (baseline) or SOF2 (progressive)
            if marker in (0xC0, 0xC2):
                height = int.from_bytes(data[pos + 5 : pos + 7], "big")
                width = int.from_bytes(data[pos + 7 : pos + 9], "big")
                return (width, height)

            if marker == 0xD9:  # End of image
                break

            # Markers without length field
            if 0xD0 <= marker <= 0xD8 or marker == 0x01:
                pos += 2
            else:
                if pos + 4 > len(data):
                    break
                length = int.from_bytes(data[pos + 2 : pos + 4], "big")
                pos += 2 + length

        return (0, 0)

    def _download_artwork(self, url: str) -> bytes | None:
        """Download artwork, requesting JPEG format from Google servers."""
        jpeg_url = self._force_jpeg_url(url)
        client = self._get_http_client()

        try:
            response = client.get(jpeg_url)
            response.raise_for_status()
            data = response.content

            if self._detect_mime_type(data) == "image/jpeg":
                return data

            # Fallback to original URL only if we modified it
            if jpeg_url == url:
                return data

            logger.debug("JPEG request failed, trying original URL")
            response = client.get(url)
            response.raise_for_status()
            return response.content

        except Exception as e:
            logger.debug("Failed to download artwork: {}", e)
            return None

    def _create_picture(self, data: bytes, width: int, height: int) -> Picture:
        """Create a FLAC-style Picture for Ogg/Opus/FLAC formats."""
        pic = Picture()
        pic.type = 3  # Front cover
        pic.mime = "image/jpeg"
        pic.width = width
        pic.height = height
        pic.depth = 24  # RGB
        pic.data = data
        return pic

    def _embed_artwork(self, file_path: Path, image_data: bytes) -> bool:
        """Embed artwork into audio file based on format."""
        if self._detect_mime_type(image_data) != "image/jpeg":
            logger.warning("Artwork is not JPEG format, skipping embed")
            return False

        suffix = file_path.suffix.lower()
        img_width, img_height = self._get_jpeg_dimensions(image_data)

        try:
            if suffix == ".mp3":
                audio = ID3(str(file_path))
                audio.delall("APIC")
                audio.add(
                    APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=image_data,
                    )
                )
                audio.save()

            elif suffix in {".m4a", ".mp4"}:
                audio = MutagenFile(str(file_path))
                if audio is not None:
                    audio["covr"] = [
                        MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)
                    ]
                    audio.save()

            elif suffix == ".flac":
                audio = MutagenFile(str(file_path))
                if audio is not None:
                    audio.clear_pictures()
                    audio.add_picture(
                        self._create_picture(image_data, img_width, img_height)
                    )
                    audio.save()

            elif suffix in {".opus", ".ogg"}:
                audio_cls = OggOpus if suffix == ".opus" else OggVorbis
                audio = audio_cls(str(file_path))
                pic = self._create_picture(image_data, img_width, img_height)
                audio["metadata_block_picture"] = [
                    base64.b64encode(pic.write()).decode("ascii")
                ]
                audio.save()

            else:
                logger.debug("Unsupported format for artwork: {}", suffix)
                return False

            return True

        except Exception as e:
            logger.warning("Failed to embed artwork in {}: {}", file_path.name, e)
            return False

    def patch_file(
        self,
        file_path: Path,
        metadata: TrackMetadata,
        playlist_name: str,
    ) -> bool:
        """Update audio file metadata with enriched values."""
        try:
            audio = MutagenFile(str(file_path), easy=True)
            if audio is None:
                logger.warning("Could not open file for patching: {}", file_path)
                return False

            audio["title"] = metadata.title
            audio["artist"] = metadata.artist
            audio["album"] = metadata.album or playlist_name
            audio["albumartist"] = metadata.artist
            audio["tracknumber"] = str(metadata.track_number)
            audio.save()

            if metadata.thumbnail_url:
                logger.debug("Downloading artwork for: {}", file_path.name)
                image_data = self._download_artwork(metadata.thumbnail_url)
                if image_data:
                    logger.debug("Downloaded {} bytes of artwork", len(image_data))
                    if self._embed_artwork(file_path, image_data):
                        logger.debug("Artwork embedded successfully")
                    else:
                        logger.warning(
                            "Failed to embed artwork for: {}", file_path.name
                        )
                else:
                    logger.warning("Artwork download failed for: {}", file_path.name)

            logger.debug("Patched metadata for: {}", file_path.name)
            return True

        except Exception as e:
            logger.error("Failed to patch {}: {}", file_path, e)
            return False

    def patch_files(
        self,
        file_paths: Sequence[Path],
        track_metadata: Sequence[TrackMetadata],
        playlist_name: str,
    ) -> int:
        """Patch multiple files with corresponding metadata."""
        if len(file_paths) != len(track_metadata):
            logger.warning(
                "File count ({}) doesn't match metadata count ({}). "
                "Patching {} files with available metadata.",
                len(file_paths),
                len(track_metadata),
                min(len(file_paths), len(track_metadata)),
            )

        patched = 0
        for file_path, metadata in zip(file_paths, track_metadata, strict=False):
            if self.patch_file(file_path, metadata, playlist_name):
                patched += 1

        unmatched = len(file_paths) - min(len(file_paths), len(track_metadata))
        if unmatched > 0:
            logger.warning(
                "Patched {}/{} files ({} files had no matching metadata)",
                patched,
                len(file_paths),
                unmatched,
            )
        else:
            logger.info("Patched {}/{} files", patched, len(file_paths))

        return patched
