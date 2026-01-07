# Playlist Support - Implementation Plan

> **Date:** 2026-01-06
> **Status:** Ready for Implementation
> **Branch:** feat/playlists

## Table of Contents

1. [Overview](#overview) - V1 scope and future plans
2. [URL Detection & Classification](#url-detection--classification) - How to identify albums vs playlists
3. [ytmusicapi Test Results](#ytmusicapi-test-results) - Real API response data
4. [Architecture](#architecture) - Data flow diagram and tool responsibilities
5. [File Structure](#file-structure) - Output paths, metadata, M3U format
6. [Configuration](#configuration) - UI toggle and beets config
7. [Implementation Details](#implementation-details) - Complete code for all services
8. [API Changes](#api-changes) - Schema and router updates
9. [Frontend Changes](#frontend-changes) - Experimental toggle UI
10. [Dependencies](#dependencies) - Python packages to add
11. [Files Summary](#files-summary) - Quick reference of files to create/modify
12. [Testing](#testing) - Unit tests and integration test URLs
13. [Limitations](#limitations--known-issues) - Known constraints
14. [Rollout Plan](#rollout-plan) - Implementation order

---

## Quick Reference

| Item | Value |
|------|-------|
| **Classification** | `OLAK5uy_*` = Album, everything else = Playlist |
| **Output folder** | `Playlists/{playlist_name}/` |
| **Track numbering** | Continuous (skips unavailable tracks) |
| **Beets config** | `beets/playlist-config.yaml` with `move: no` |
| **New dependency** | `ytmusicapi>=1.9.0` |
| **New services** | `metadata_enricher.py`, `metadata_patcher.py`, `m3u_generator.py` |

---

## Overview

This document consolidates the POC findings and implementation decisions for YouTube Music playlist support in Yubal.

### V1 Scope

- **Playlist folder mode only** - all tracks go to `Playlists/{playlist_name}/`
- **Enriched metadata** - ytmusicapi provides clean album/artist/title
- **Beets enrichment** - additional metadata (genres, MusicBrainz IDs)
- **M3U generation** - playlist file for easy playback
- **Visual URL type detection** - button changes based on album vs playlist URL with "beta" badge

### Future Scope (Not V1)

- Album folder mode (scatter tracks to `{artist}/{album}/`)
- Per-import mode selection
- Configurable via UI (currently ENV var only)

---

## URL Detection & Classification

### YouTube Music URL Structure

YouTube Music uses the same URL format for both albums and playlists:

```
https://music.youtube.com/playlist?list={ID}
```

The `list` parameter prefix determines the content type:

| Prefix | Type | Example |
|--------|------|---------|
| `OLAK5uy_` | Album | `playlist?list=OLAK5uy_kckr2V4...` |
| Anything else | Playlist | `playlist?list=PLxxx`, `playlist?list=RDTMAK5uy_xxx` |

### Classification Logic

**Simple rule:** If the playlist ID starts with `OLAK5uy_`, it's an album. Otherwise, it's a playlist.

```python
def classify_url(url: str) -> ImportType:
    """Classify URL - server is source of truth."""
    playlist_id = extract_playlist_id(url)

    if playlist_id.startswith("OLAK5uy_"):
        return ImportType.ALBUM

    return ImportType.PLAYLIST  # Default
```

### Validation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  CLIENT (Frontend)                                              │
│  ├─ Validates URL format (any YouTube Music playlist URL)      │
│  ├─ Detects URL type via getUrlType()                          │
│  ├─ Updates button UI (icon, text, badge) based on type        │
│  └─ Sends URL to server on submit                              │
│                              │                                  │
│                              ▼                                  │
│  SERVER (Backend) - Source of Truth                             │
│  ├─ Validates URL format                                       │
│  ├─ Extracts playlist ID                                       │
│  ├─ Classifies: OLAK5uy_* → ALBUM, else → PLAYLIST             │
│  └─ Routes to sync_album() or sync_playlist()                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### URL Type Detection

**Client (TypeScript):**
```typescript
export enum UrlType {
  ALBUM = "album",
  PLAYLIST = "playlist",
}

export function getUrlType(url: string): UrlType | null {
  const match = url.match(/list=([^&]+)/);
  const playlistId = match?.[1];
  if (!playlistId) return null;

  return playlistId.startsWith("OLAK5uy_") ? UrlType.ALBUM : UrlType.PLAYLIST;
}
```

**Server (Python):**
```python
def extract_playlist_id(url: str) -> str | None:
    """Extract playlist ID from YouTube Music URL."""
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    list_param = query.get("list", [])
    return list_param[0] if list_param else None

def is_album_url(url: str) -> bool:
    """Check if URL is an album (not playlist)."""
    playlist_id = extract_playlist_id(url)
    return playlist_id.startswith("OLAK5uy_") if playlist_id else False
```

---

## ytmusicapi Test Results

### Test Playlist

**URL:** `https://music.youtube.com/playlist?list=PLbE6wFkAlDUeDUu98GuzkCWm60QjYvagQ`
**Title:** "test123 public playlist"

### Raw API Response (`get_playlist`)

| # | Title | Artist(s) | Album | isAvailable | videoId |
|---|-------|-----------|-------|-------------|---------|
| 1 | S P E Y S I D E | Bon Iver | SABLE, fABLE | ✅ | 9cTn9Txi2JA |
| 2 | Latin Girl | Claudia Arenas | OT GALA 9 | ✅ | 2V1exaAqx-k |
| 3 | A COLD PLAY | The Kid LAROI | A COLD PLAY | ✅ | Vgpv5PtWsn4 |
| 4 | luther | Kendrick Lamar, SZA | GNX | ✅ | XVveECQmiAk |
| 5 | 40.000 de vida... | Clau | None | ❌ | **None** |
| 6 | I WAS HEARD... | Roma Gallardo | None | ❌ | **None** |
| 7 | Holocene | Bon Iver | **None** | ✅ | TWcyIpul8OE |
| 8 | Para Mí | Lucia Casani | **None** | ✅ | b_uNXFFQp3w |

### Track Classification

| Condition | Type | Action |
|-----------|------|--------|
| `isAvailable=False` OR `videoId=None` | Non-music content | Skip (don't download) |
| `isAvailable=True` AND `album=None` | Music video | Search for album |
| `isAvailable=True` AND `album={...}` | Album track | Use existing metadata |

### Search Enrichment Results

For tracks without album info, `search(filter='songs')` successfully finds album:

| Track | Artist | Search Result | Album Found |
|-------|--------|---------------|-------------|
| Holocene | Bon Iver | ✅ Match | Bon Iver, Bon Iver |
| Para Mí | Lucia Casani | ✅ Match | Para Mí |

### Expected Output Files

After processing (6 available tracks):

```
Playlists/test123 public playlist/
├── test123 public playlist.m3u
├── 01 - Bon Iver - S P E Y S I D E.opus           ← album track
├── 02 - Claudia Arenas - Latin Girl.opus          ← album track
├── 03 - The Kid LAROI - A COLD PLAY.opus          ← album track
├── 04 - Kendrick Lamar - luther.opus              ← album track (multi-artist)
├── 05 - Bon Iver - Holocene.opus                  ← enriched via search
└── 06 - Lucia Casani - Para Mí.opus               ← enriched via search
```

> **Note:** Tracks 5-6 in original playlist are skipped (`isAvailable=False`), so output tracks are renumbered 1-6 continuously.

### Key Findings

1. **Multi-artist tracks**: `artists` is an array (e.g., `[{name: "Kendrick Lamar"}, {name: "SZA"}]`). We use first artist for filename, but could join for metadata.
2. **Non-music detection**: `isAvailable=False` AND `videoId=None` reliably identifies non-music content.
3. **Search accuracy**: First search result with matching artist is reliable for album lookup.
4. **Thumbnails**: Available for all tracks (1-2 per track), can be used for album art.

---

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PLAYLIST IMPORT FLOW                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. FETCH METADATA (ytmusicapi)                                         │
│     ┌──────────────────┐                                                │
│     │ get_playlist()   │ → Clean titles, artists for ALL tracks         │
│     │                  │ → Album info for album-tracks                  │
│     │                  │ → isAvailable flag for non-music content       │
│     └────────┬─────────┘                                                │
│              │                                                          │
│              ▼                                                          │
│  2. ENRICH MISSING ALBUMS (ytmusicapi)                                  │
│     ┌──────────────────┐                                                │
│     │ search(filter=   │ → For tracks without album (music videos)      │
│     │   'songs')       │ → Find album version, extract album name       │
│     │                  │ → Validate artist matches                      │
│     └────────┬─────────┘                                                │
│              │                                                          │
│              ▼                                                          │
│  3. DOWNLOAD (yt-dlp)                                                   │
│     ┌──────────────────┐                                                │
│     │ download_album() │ → Download audio files                         │
│     │                  │ → Extract audio (FFmpeg)                       │
│     │                  │ → Embed playlist thumbnail                     │
│     └────────┬─────────┘                                                │
│              │                                                          │
│              ▼                                                          │
│  4. PATCH METADATA (mutagen)                                            │
│     ┌──────────────────┐                                                │
│     │ patch_metadata() │ → Overwrite with enriched data:                │
│     │                  │   • title (clean)                              │
│     │                  │   • artist (from ytmusicapi)                   │
│     │                  │   • album (from search or original)            │
│     │                  │   • track number (playlist index)              │
│     └────────┬─────────┘                                                │
│              │                                                          │
│              ▼                                                          │
│  5. ORGANIZE FILES                                                      │
│     ┌──────────────────┐                                                │
│     │ move to          │ → Playlists/{playlist_name}/                   │
│     │ destination      │ → Filename: {index} - {artist} - {title}.opus  │
│     └────────┬─────────┘                                                │
│              │                                                          │
│              ▼                                                          │
│  6. BEETS IMPORT                                                        │
│     ┌──────────────────┐                                                │
│     │ beet import      │ → Uses playlist-config.yaml (move: no)         │
│     │ (move: no)       │ → Enriches metadata in-place:                  │
│     │                  │   • MusicBrainz matching                       │
│     │                  │   • LastFM genres                              │
│     │                  │   • Normalized spelling                        │
│     └────────┬─────────┘                                                │
│              │                                                          │
│              ▼                                                          │
│  7. DOWNLOAD ALBUM ART                                                  │
│     ┌──────────────────┐                                                │
│     │ embed_album_art()│ → Fetch individual album art per track         │
│     │                  │ → Embed into audio files                       │
│     └────────┬─────────┘                                                │
│              │                                                          │
│              ▼                                                          │
│  8. GENERATE M3U                                                        │
│     ┌──────────────────┐                                                │
│     │ generate_m3u()   │ → Create {playlist_name}.m3u                   │
│     │                  │ → Relative paths to tracks                     │
│     └──────────────────┘                                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Tool Responsibilities

| Tool | Purpose | Why Needed |
|------|---------|------------|
| **ytmusicapi** | Metadata enrichment | Clean titles/artists, album search |
| **yt-dlp** | File download | Audio extraction, thumbnail download |
| **mutagen** | Metadata patching | Write enriched data to audio files |
| **beets** | Further enrichment | MusicBrainz, genres, normalization |

---

## File Structure

### Output Structure

```
data/
├── {artist}/                      # Album imports (existing)
│   └── {year} - {album}/
│       └── {track} - {title}.opus
│
└── Playlists/                     # Playlist imports (new)
    └── {playlist_name}/
        ├── {playlist_name}.m3u    # M3U playlist file
        ├── 01 - Bon Iver - S P E Y S I D E.opus
        ├── 02 - Claudia Arenas - Latin Girl.opus
        ├── 03 - The Kid LAROI - A COLD PLAY.opus
        └── ...
```

### Embedded Metadata (per track)

```
title:       S P E Y S I D E           ← Clean title from ytmusicapi
artist:      Bon Iver                   ← From ytmusicapi artists[0]
album:       SABLE, fABLE               ← From ytmusicapi search (enriched)
tracknumber: 1                          ← Playlist index (not album track)
genre:       Indie Folk                 ← From beets/LastFM
artwork:     [individual album art]     ← Per-track album artwork
```

### M3U Format

```m3u
#EXTM3U
#PLAYLIST:test123 public playlist
#EXTINF:210,Bon Iver - S P E Y S I D E
01 - Bon Iver - S P E Y S I D E.opus
#EXTINF:163,Claudia Arenas - Latin Girl
02 - Claudia Arenas - Latin Girl.opus
#EXTINF:180,The Kid LAROI - A COLD PLAY
03 - The Kid LAROI - A COLD PLAY.opus
#EXTINF:178,Kendrick Lamar - luther
04 - Kendrick Lamar - luther.opus
#EXTINF:344,Bon Iver - Holocene
05 - Bon Iver - Holocene.opus
#EXTINF:200,Lucia Casani - Para Mí
06 - Lucia Casani - Para Mí.opus
```

---

## Configuration

### Always Enabled

Playlist support is **always enabled** - both album and playlist URLs are accepted without any toggles or confirmation dialogs. The UI provides visual feedback to indicate URL type.

> **Note:** V1 only supports playlist folder mode. The `YUBAL_PLAYLIST_MODE` env var is reserved for future use when album folder mode is implemented.

### Beets Configuration

**New file:** `beets/playlist-config.yaml`

```yaml
# Beets configuration for playlist imports
# Key difference: move: no (enrich metadata in-place)

directory: /data
library: /data/beets-library.db

import:
  move: no          # Don't move files - they're already in Playlists/
  copy: no          # Don't copy either
  write: yes        # Write metadata to files
  autotag: yes      # Still try to match for enrichment
  quiet: yes        # Non-interactive
  quiet_fallback: asis  # Import as-is if no match

paths:
  default: $albumartist/$album%aunique{}/$track - $title
  singleton: Non-Album/$artist - $title
  comp: Compilations/$album%aunique{}/$track - $title

plugins:
  - spotify
  - fetchart
  - lastgenre
  - zero

spotify:
  source_weight: 0.5

lastgenre:
  auto: yes
  source: track

fetchart:
  auto: no  # We handle artwork separately (per-track)

zero:
  fields: comments
  update_database: true
```

---

## Implementation Details

### 1. MetadataEnricher Service

**File:** `yubal/services/metadata_enricher.py`

```python
"""YouTube Music metadata enrichment using ytmusicapi."""

import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from loguru import logger
from ytmusicapi import YTMusic


@dataclass
class EnrichedTrack:
    """Track with enriched metadata from YouTube Music."""

    video_id: str
    title: str
    artist: str
    album: str | None
    album_art_url: str | None  # For individual album art
    is_available: bool
    playlist_index: int


class MetadataEnricher:
    """Enriches playlist track metadata using YouTube Music API."""

    def __init__(self, request_delay: float = 0.5):
        self.yt = YTMusic()
        self.request_delay = request_delay

    def enrich_playlist(self, playlist_id: str) -> tuple[str, list[EnrichedTrack]]:
        """Fetch and enrich all tracks in a playlist.

        Returns:
            Tuple of (playlist_title, list of EnrichedTrack)
            Only available tracks are returned, with continuous numbering.
        """
        logger.info("Enriching playlist metadata: {}", playlist_id)

        playlist = self.yt.get_playlist(playlist_id)
        playlist_title = playlist.get("title", "Unknown Playlist")
        tracks = playlist.get("tracks", [])
        enriched: list[EnrichedTrack] = []
        search_count = 0
        available_index = 0  # Continuous index for available tracks only

        for track in tracks:
            video_id = track.get("videoId")
            is_available = track.get("isAvailable", False)

            # Skip non-music content (no videoId or not available)
            if not is_available or not video_id:
                logger.debug("Skipping unavailable track: {}", track.get("title"))
                continue

            available_index += 1
            title = track.get("title", "")
            artist = self._get_artist(track)

            # Get album from playlist data (works for album tracks)
            album = None
            album_art_url = None
            if track.get("album"):
                album = track["album"].get("name")

            # Extract album art URL from thumbnails
            thumbnails = track.get("thumbnails", [])
            if thumbnails:
                # Get highest quality thumbnail
                album_art_url = thumbnails[-1].get("url")

            # If missing album, search for it (music videos need this)
            if not album and artist and title:
                if search_count > 0 and self.request_delay > 0:
                    time.sleep(self.request_delay)

                search_result = self._search_track(artist, title)
                if search_result:
                    album = search_result.get("album")
                    if not album_art_url and search_result.get("album_art_url"):
                        album_art_url = search_result["album_art_url"]
                search_count += 1

            enriched.append(EnrichedTrack(
                video_id=video_id,
                title=title,
                artist=artist,
                album=album,
                album_art_url=album_art_url,
                is_available=True,
                playlist_index=available_index,  # Continuous numbering
            ))

        logger.info(
            "Enriched {} tracks ({} searches performed)",
            len(enriched),
            search_count,
        )
        return playlist_title, enriched

    def _get_artist(self, track: dict) -> str:
        """Extract primary artist name from track data."""
        artists = track.get("artists", [])
        if artists and artists[0]:
            return artists[0].get("name", "")
        return ""

    def _search_track(self, artist: str, title: str) -> dict | None:
        """Search for track to get album info."""
        try:
            query = f"{artist} {title}"
            results = self.yt.search(query, filter="songs", limit=1)

            if not results:
                return None

            result = results[0]

            # Verify artist matches
            result_artists = [a.get("name", "") for a in result.get("artists", [])]
            if artist not in result_artists:
                return None

            album_info = result.get("album", {})
            thumbnails = result.get("thumbnails", [])

            return {
                "album": album_info.get("name") if album_info else None,
                "album_art_url": thumbnails[-1].get("url") if thumbnails else None,
            }

        except Exception as e:
            logger.warning("Search failed for '{}': {}", title, e)
            return None


def extract_playlist_id(url: str) -> str | None:
    """Extract playlist ID from a YouTube Music URL."""
    parsed = urlparse(url)

    if "youtube" not in parsed.netloc:
        return None

    query = parse_qs(parsed.query)
    list_param = query.get("list", [])

    if list_param:
        return list_param[0]

    return None


def is_playlist_url(url: str) -> bool:
    """Check if URL is a playlist (not album).

    Albums start with OLAK5uy_. Everything else is a playlist.
    """
    playlist_id = extract_playlist_id(url)
    if not playlist_id:
        return False

    # Albums start with OLAK5uy_ - everything else is a playlist
    return not playlist_id.startswith("OLAK5uy_")
```

### 2. Metadata Patcher

**File:** `yubal/services/metadata_patcher.py`

```python
"""Patch audio file metadata using mutagen."""

from pathlib import Path

from loguru import logger
from mutagen import File as MutagenFile

from yubal.services.metadata_enricher import EnrichedTrack


def patch_track_metadata(audio_file: Path, track: EnrichedTrack) -> bool:
    """Patch a single audio file with enriched metadata.

    Args:
        audio_file: Path to the audio file
        track: Enriched track metadata

    Returns:
        True if successful, False otherwise
    """
    try:
        audio = MutagenFile(str(audio_file), easy=True)
        if audio is None:
            logger.warning("Could not open audio file: {}", audio_file)
            return False

        # Update metadata
        audio["title"] = track.title
        audio["artist"] = track.artist
        audio["tracknumber"] = str(track.playlist_index)

        if track.album:
            audio["album"] = track.album

        audio.save()
        logger.debug("Patched metadata for: {}", audio_file.name)
        return True

    except Exception as e:
        logger.warning("Failed to patch {}: {}", audio_file.name, e)
        return False


def patch_playlist_metadata(
    audio_files: list[Path],
    tracks: list[EnrichedTrack],
) -> int:
    """Patch metadata for all tracks in a playlist.

    Args:
        audio_files: Downloaded audio files (in playlist order)
        tracks: Enriched track metadata (in same order, only available tracks)

    Returns:
        Number of successfully patched files
    """
    success_count = 0

    for audio_file, track in zip(audio_files, tracks):
        if patch_track_metadata(audio_file, track):
            success_count += 1

    logger.info("Patched {}/{} files", success_count, len(audio_files))
    return success_count
```

### 3. M3U Generator

**File:** `yubal/services/m3u_generator.py`

```python
"""Generate M3U playlist files."""

from pathlib import Path

from loguru import logger

from yubal.services.metadata_enricher import EnrichedTrack


def generate_m3u(
    playlist_dir: Path,
    playlist_name: str,
    tracks: list[EnrichedTrack],
    audio_files: list[Path],
) -> Path:
    """Generate an M3U playlist file.

    Args:
        playlist_dir: Directory containing the playlist files
        playlist_name: Name of the playlist
        tracks: Enriched track metadata (only available tracks)
        audio_files: Downloaded audio files

    Returns:
        Path to the generated M3U file
    """
    m3u_path = playlist_dir / f"{playlist_name}.m3u"

    lines = [
        "#EXTM3U",
        f"#PLAYLIST:{playlist_name}",
    ]

    for track, audio_file in zip(tracks, audio_files):
        # EXTINF format: #EXTINF:duration,artist - title
        # Duration -1 means unknown
        lines.append(f"#EXTINF:-1,{track.artist} - {track.title}")
        lines.append(audio_file.name)

    m3u_content = "\n".join(lines) + "\n"
    m3u_path.write_text(m3u_content, encoding="utf-8")

    logger.info("Generated M3U: {}", m3u_path)
    return m3u_path
```

### 4. Sync Service Integration

**File:** `yubal/services/sync.py` (additions)

```python
# Add to imports
from yubal.services.metadata_enricher import (
    MetadataEnricher,
    EnrichedTrack,
    is_playlist_url,
    extract_playlist_id,
)
from yubal.services.metadata_patcher import patch_playlist_metadata
from yubal.services.m3u_generator import generate_m3u


class SyncService:
    # ... existing code ...

    def sync_playlist(
        self,
        url: str,
        job_id: str,
        progress_callback: ProgressCallback | None = None,
        cancel_check: CancelCheck | None = None,
    ) -> SyncResult:
        """Download and organize a playlist with metadata enrichment."""

        playlist_id = extract_playlist_id(url)
        if not playlist_id:
            return SyncResult(success=False, error="Invalid playlist URL")

        job_temp_dir = self.temp_dir / job_id
        job_temp_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Phase 1: Enrich metadata (returns only available tracks)
            self._report_progress(progress_callback, ProgressStep.FETCHING_INFO,
                                  "Enriching playlist metadata...", 0.0)

            enricher = MetadataEnricher()
            playlist_title, tracks = enricher.enrich_playlist(playlist_id)

            if not tracks:
                return SyncResult(success=False, error="No available tracks in playlist")

            # Phase 2: Download
            self._report_progress(progress_callback, ProgressStep.DOWNLOADING,
                                  f"Downloading {len(tracks)} tracks...", 0.1)

            download_result = self.downloader.download_album(
                url=url,
                output_dir=job_temp_dir,
                progress_callback=progress_callback,
                cancel_check=cancel_check,
            )

            if not download_result.success:
                return SyncResult(success=False, error=download_result.error)

            # Phase 3: Patch metadata
            self._report_progress(progress_callback, ProgressStep.IMPORTING,
                                  "Patching metadata...", 0.5)

            audio_files = sorted(job_temp_dir.glob("*.opus"))
            patch_playlist_metadata(audio_files, tracks)

            # Phase 4: Move to playlist folder
            playlist_dir = self.data_dir / "Playlists" / self._sanitize_filename(playlist_title)
            playlist_dir.mkdir(parents=True, exist_ok=True)

            final_files = []
            for audio_file, track in zip(audio_files, tracks):
                # Rename using track's playlist_index (already continuous)
                new_name = f"{track.playlist_index:02d} - {track.artist} - {track.title}.opus"
                new_name = self._sanitize_filename(new_name)
                dest = playlist_dir / new_name
                shutil.move(str(audio_file), str(dest))
                final_files.append(dest)

            # Phase 5: Run beets (with playlist config)
            self._report_progress(progress_callback, ProgressStep.IMPORTING,
                                  "Running beets enrichment...", 0.7)

            beets_config = self.beets_dir / "playlist-config.yaml"
            self._run_beets_import(playlist_dir, config_path=beets_config)

            # Phase 6: Download and embed album art
            self._report_progress(progress_callback, ProgressStep.IMPORTING,
                                  "Embedding album artwork...", 0.85)

            self._embed_album_art(final_files, tracks)

            # Phase 7: Generate M3U
            self._report_progress(progress_callback, ProgressStep.IMPORTING,
                                  "Generating playlist file...", 0.95)

            generate_m3u(playlist_dir, playlist_title, tracks, final_files)

            return SyncResult(
                success=True,
                output_path=str(playlist_dir),
            )

        except Exception as e:
            logger.exception("Playlist sync failed")
            return SyncResult(success=False, error=str(e))

        finally:
            if job_temp_dir.exists():
                shutil.rmtree(job_temp_dir, ignore_errors=True)

    def _embed_album_art(
        self,
        audio_files: list[Path],
        tracks: list[EnrichedTrack],
    ) -> None:
        """Download and embed individual album art for each track."""
        import requests
        from mutagen.oggopus import OggOpus
        from mutagen.flac import Picture
        import base64

        for audio_file, track in zip(audio_files, tracks):
            if not track.album_art_url:
                continue

            try:
                # Download artwork
                response = requests.get(track.album_art_url, timeout=10)
                if response.status_code != 200:
                    continue

                # Embed in Opus file
                audio = OggOpus(str(audio_file))

                picture = Picture()
                picture.data = response.content
                picture.type = 3  # Cover (front)
                picture.mime = "image/jpeg"
                picture.desc = "Cover"

                audio["metadata_block_picture"] = [
                    base64.b64encode(picture.write()).decode("ascii")
                ]
                audio.save()

                logger.debug("Embedded album art for: {}", audio_file.name)

            except Exception as e:
                logger.warning("Failed to embed art for {}: {}", audio_file.name, e)

    def _sanitize_filename(self, name: str) -> str:
        """Remove invalid filename characters."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "")
        return name.strip()
```

---

## API Changes

### Job Creation Schema

**File:** `yubal/schemas/jobs.py`

```python
from pydantic import BaseModel
from yubal.core.enums import ImportType


class CreateJobRequest(BaseModel):
    url: str
    import_type: ImportType = ImportType.ALBUM  # Default to album


class ImportType(str, Enum):
    ALBUM = "album"
    PLAYLIST = "playlist"
```

### Job Router

**File:** `yubal/api/routes/jobs.py`

```python
@router.post("/")
async def create_job(request: CreateJobRequest):
    # Route to appropriate sync method based on import_type
    job = job_service.create_job(
        url=request.url,
        import_type=request.import_type,
    )
    return job
```

The backend accepts both album and playlist URLs. The frontend detects URL type and provides visual feedback.

---

## Frontend Changes

### Visual URL Type Detection

The frontend detects URL type and provides visual feedback via the download button. No toggles or dialogs.

**File:** `web/src/lib/url.ts`

```typescript
export enum UrlType {
  ALBUM = "album",
  PLAYLIST = "playlist",
}

export function getUrlType(url: string): UrlType | null {
  const match = url.match(/list=([^&]+)/);
  const playlistId = match?.[1];
  if (!playlistId) return null;

  return playlistId.startsWith("OLAK5uy_") ? UrlType.ALBUM : UrlType.PLAYLIST;
}
```

**File:** `web/src/App.tsx`

```tsx
import { match } from "ts-pattern";
import { getUrlType, UrlType } from "./lib/url";

// Detect URL type
const urlType = canSync ? getUrlType(url) : null;

// Dynamic icon based on type
const startContent = match(urlType)
  .with(UrlType.ALBUM, () => <Disc3 className="h-4 w-4" />)
  .with(UrlType.PLAYLIST, () => <ListMusic className="h-4 w-4" />)
  .otherwise(() => <Download className="h-4 w-4" />);

// Dynamic button text
const children = match(urlType)
  .with(UrlType.ALBUM, () => "Download album")
  .with(UrlType.PLAYLIST, () => "Download playlist")
  .otherwise(() => "Download");

// Button with beta badge for playlists
<Badge color="danger" content="beta" size="sm" isInvisible={urlType !== UrlType.PLAYLIST}>
  <Button color="primary" radius="full" onPress={handleSync} isDisabled={!canSync} startContent={startContent}>
    {children}
  </Button>
</Badge>
```

**Behavior:**

| URL Type | Icon | Button Text | Badge |
|----------|------|-------------|-------|
| Album (`OLAK5uy_*`) | Disc3 | "Download album" | None |
| Playlist (other) | ListMusic | "Download playlist" | "beta" |
| Invalid/empty | Download | "Download" (disabled) | None |

---

## Dependencies

### Python Dependencies

**File:** `pyproject.toml`

```toml
dependencies = [
    # ... existing deps
    "ytmusicapi>=1.9.0",  # YouTube Music API for playlist metadata
    "mutagen>=1.47.0",     # Already present for beets, but explicit
]
```

After editing:
```bash
uv sync
```

---

## Files Summary

| File | Action | Description |
|------|--------|-------------|
| `pyproject.toml` | Edit | Add `ytmusicapi>=1.9.0` |
| `yubal/core/enums.py` | Edit | Add `ImportType` enum |
| `yubal/services/metadata_enricher.py` | Create | ytmusicapi enrichment service |
| `yubal/services/metadata_patcher.py` | Create | mutagen metadata patching |
| `yubal/services/m3u_generator.py` | Create | M3U playlist generation |
| `yubal/services/sync.py` | Edit | Add `sync_playlist()` method |
| `yubal/schemas/jobs.py` | Edit | Add `import_type` field |
| `yubal/api/routes/jobs.py` | Edit | Handle playlist import type |
| `beets/playlist-config.yaml` | Create | Beets config for playlists |
| `web/src/lib/url.ts` | Edit | Add `UrlType` enum and `getUrlType()` function |
| `web/src/App.tsx` | Edit | Add visual URL type detection (icon, text, badge) |
| `tests/test_metadata_enricher.py` | Create | Unit tests |

---

## Testing

### Unit Tests

```python
# tests/test_metadata_enricher.py

import pytest
from yubal.services.metadata_enricher import (
    extract_playlist_id,
    is_playlist_url,
)


class TestExtractPlaylistId:
    def test_playlist_url(self):
        url = "https://music.youtube.com/playlist?list=PLxxx"
        assert extract_playlist_id(url) == "PLxxx"

    def test_album_url(self):
        url = "https://music.youtube.com/playlist?list=OLAK5uy_xxx"
        assert extract_playlist_id(url) == "OLAK5uy_xxx"

    def test_watch_url_returns_none(self):
        url = "https://music.youtube.com/watch?v=xxx"
        assert extract_playlist_id(url) is None


class TestIsPlaylistUrl:
    def test_user_playlist_returns_true(self):
        assert is_playlist_url("https://music.youtube.com/playlist?list=PLxxx")

    def test_album_returns_false(self):
        assert not is_playlist_url("https://music.youtube.com/playlist?list=OLAK5uy_xxx")

    def test_radio_mix_returns_true(self):
        # Anything not starting with OLAK5uy_ is a playlist
        assert is_playlist_url("https://music.youtube.com/playlist?list=RDTMAK5uy_xxx")

    def test_unknown_prefix_returns_true(self):
        # Default to playlist for unknown prefixes
        assert is_playlist_url("https://music.youtube.com/playlist?list=FUTURE_PREFIX_xxx")
```

### Integration Test URLs

```python
# Album (existing flow)
album_url = "https://music.youtube.com/playlist?list=OLAK5uy_kckr2V4WvGQVbCsUNmNSLgYIM_od9SoFs"

# Playlist - music videos (needs enrichment)
playlist_no_meta = "https://music.youtube.com/playlist?list=PL4fGSI1pDJn6sMPCoD7PdSlEgyUylgxuT"

# Playlist - album tracks (already has metadata)
playlist_with_meta = "https://music.youtube.com/playlist?list=PLbE6wFkAlDUeDUu98GuzkCWm60QjYvagQ"
```

---

## Limitations & Known Issues

### Rate Limiting
- ytmusicapi searches add ~0.5s per track needing enrichment
- 100-track playlist = ~50s enrichment time
- Acceptable for V1, consider caching for V2

### Metadata Accuracy
- Search-based enrichment is "best effort"
- May get wrong album for covers/remixes
- Artist name validation reduces false matches

### Non-Music Content
- Videos with `isAvailable=False` or `videoId=None` are skipped entirely
- Gaming streams, vlogs won't be downloaded
- Only music tracks appear in final output

### Track Numbers
- Uses playlist index (1, 2, 3...) not album track number
- Makes sense for playlist organization
- Real album track number available in beets database

---

## Rollout Plan

1. **Add frontend URL type detection** - `UrlType` enum, `getUrlType()`, visual button changes ✅
2. **Implement core services** (metadata_enricher, metadata_patcher, m3u_generator)
3. **Add sync_playlist()** to sync service
4. **Create playlist-config.yaml** for beets
5. **Add API changes** (import_type field)
6. **Test with known playlists**
7. **Deploy** - playlists work immediately with "beta" badge indicator

---

## Related Documents

These documents contain the original research and can be archived after implementation:

- `docs/playlist-support-poc.md` - Original POC findings and metadata analysis
- `docs/ytmusicapi-enrichment-implementation.md` - Initial ytmusicapi research

This document (`playlist-implementation-plan.md`) consolidates and supersedes both.
