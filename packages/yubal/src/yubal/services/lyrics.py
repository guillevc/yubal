"""Lyrics fetching service using lrclib.net."""

import logging
from pathlib import Path
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


class LyricsServiceProtocol(Protocol):
    """Protocol for lyrics fetching services.

    Enables dependency injection and testing of lyrics functionality.
    """

    def fetch_lyrics(
        self,
        title: str,
        artist: str,
        duration_seconds: int,
    ) -> str | None:
        """Fetch lyrics for a track."""
        ...

    def save_lyrics(self, lyrics: str, audio_path: Path) -> Path:
        """Save lyrics to disk."""
        ...


class LyricsService:
    """Service for fetching synced lyrics from lrclib.net.

    lrclib.net is a free, open lyrics database that provides time-synced
    lyrics in LRC format. This service fetches lyrics by matching track
    title, artist, and duration.

    Example:
        >>> service = LyricsService()
        >>> lyrics = service.fetch_lyrics("Bohemian Rhapsody", "Queen", 354)
        >>> if lyrics:
        ...     service.save_lyrics(lyrics, Path("01 - Bohemian Rhapsody.opus"))
    """

    LRCLIB_API = "https://lrclib.net/api/get"
    TIMEOUT = 10  # seconds

    def fetch_lyrics(
        self,
        title: str,
        artist: str,
        duration_seconds: int,
    ) -> str | None:
        """Fetch synced lyrics for a track from lrclib.net.

        Makes a GET request to lrclib.net with track metadata. Prefers
        synced lyrics (with timestamps) over plain lyrics.

        Args:
            title: Track title.
            artist: Primary artist name.
            duration_seconds: Track duration in seconds.

        Returns:
            LRC-formatted lyrics string if found, None otherwise.
            Returns synced lyrics if available, falls back to plain lyrics.
        """
        params = {
            "track_name": title,
            "artist_name": artist,
            "duration": duration_seconds,
        }

        try:
            response = httpx.get(
                self.LRCLIB_API,
                params=params,
                timeout=self.TIMEOUT,
            )

            if response.status_code == 404:
                logger.debug(
                    "No lyrics found for '%s' by %s",
                    title,
                    artist,
                )
                return None

            response.raise_for_status()
            data = response.json()

            # Prefer synced lyrics over plain lyrics
            lyrics = data.get("syncedLyrics") or data.get("plainLyrics")

            if not lyrics:
                logger.debug(
                    "Empty lyrics response for '%s' by %s",
                    title,
                    artist,
                )
                return None

            return lyrics

        except httpx.TimeoutException:
            logger.debug(
                "Lyrics fetch timed out for '%s' by %s",
                title,
                artist,
            )
            return None
        except httpx.HTTPStatusError as e:
            logger.debug(
                "Lyrics fetch HTTP error for '%s' by %s: %s",
                title,
                artist,
                e,
            )
            return None
        except httpx.RequestError as e:
            logger.debug(
                "Lyrics fetch request error for '%s' by %s: %s",
                title,
                artist,
                e,
            )
            return None

    def save_lyrics(self, lyrics: str, audio_path: Path) -> Path:
        """Save lyrics to an LRC file alongside the audio file.

        Creates an .lrc file with the same name as the audio file.
        For example, "01 - Track.opus" becomes "01 - Track.lrc".

        Args:
            lyrics: LRC-formatted lyrics string.
            audio_path: Path to the audio file.

        Returns:
            Path to the saved .lrc file.
        """
        lrc_path = audio_path.with_suffix(".lrc")
        lrc_path.write_text(lyrics, encoding="utf-8")
        return lrc_path
