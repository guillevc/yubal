# YouTube Music Playlist Support - POC Findings & Implementation Plan

> **Date:** 2025-01-02
> **Status:** POC Complete, Ready for Implementation

## Executive Summary

This document captures the research and POC testing for adding YouTube Music **playlist** support to Yubal. The key finding is that playlists require fundamentally different handling than albums due to metadata availability differences in yt-dlp.

---

## Part 1: Problem Statement

### Current State
- Yubal currently supports YouTube Music **albums**
- Albums work well because yt-dlp provides rich metadata (album, artist, track)
- Beets + Spotify successfully enriches and organizes album tracks

### Goal
- Add support for YouTube Music **playlists** (e.g., "Trending 20 Spain")
- Playlists contain tracks from different albums/artists
- Need a strategy for organizing and tagging these mixed tracks

---

## Part 2: POC Testing Results

### Test URLs Used

| Type | URL | Title |
|------|-----|-------|
| Album | `https://music.youtube.com/playlist?list=OLAK5uy_kqKSSUvhqlZJQUlvZzxdhm4fXg7mLtpVQ` | LUX by ROSALÍA |
| Playlist | `https://music.youtube.com/playlist?list=OLAK5uy_mzYnlaHgFOvLaxqIPnnouEr-idiUn4NIM` | Trending 20 Spain |

### Key Finding: Same Song, Different Metadata

We tested "La Perla" by ROSALÍA in both contexts:
- **Album track** (Track 7 in LUX album)
- **Playlist track** (Track 2 in Trending 20 Spain)

| Field | Album Track | Playlist Track |
|-------|-------------|----------------|
| `album` | `"LUX"` | `None` |
| `artist` | `"ROSALÍA, Yahritza Y Su Esencia"` | `None` |
| `artists` | `['ROSALÍA', 'Yahritza Y Su Esencia']` | `None` |
| `track` | `"La Perla"` | `None` |
| `channel` | `"ROSALÍA"` | `"ROSALÍA"` |
| `creators` | `['ROSALÍA', 'Yahritza Y Su Esencia']` | `None` |
| `release_year` | `2025` | `2025` |
| `title` | `"La Perla"` | `"ROSALÍA - La Perla (Official Video) ft. Yahritza Y Su Esencia"` |
| Video ID | `w7pjt9ZH3NM` | `GkTWxDB21cA` |

### Critical Insight: Different Video IDs

- **Album tracks** point to album-specific audio versions with rich metadata
- **Playlist tracks** point to music videos with minimal metadata
- These are literally different videos on YouTube's backend

### Available Fields for Playlist Tracks

From full extraction of playlist track:
```
channel: ROSALÍA              # Artist (reliable)
title: ROSALÍA - La Perla (Official Video) ft. Yahritza Y Su Esencia  # Messy
description: Contains 'LUX' Out Now...  # Sometimes has album hint
tags: ['ROSALÍA', 'LUX', ...]  # Sometimes has album name
release_year: 2025            # Video upload year (may differ from song release)
playlist_title: Trending 20 Spain  # Playlist name
playlist_index: 2             # Track position in playlist
```

---

## Part 3: Beets Matching Tests

### Test 1: Album Import Mode
```bash
beet import -q /tmp/yubal_playlist
# Result: "Importing as-is" - no match found
```

**Why it failed:**
- The "album" field is playlist title ("Trending 20 Spain")
- This album doesn't exist in MusicBrainz/Spotify
- Beets has nothing to match against

### Test 2: Singleton Import Mode
```bash
beet import --singleton -q /tmp/yubal_singleton
# Result: "Importing as-is" for both tracks
```

**Why it failed:**
- Messy titles make matching unreliable
- No album context for disambiguation
- Files went to `Non-Album/` with messy filenames

### Beets Matching Requirements

For reliable matching, beets needs:
1. **Clean title** - just the song name
2. **Artist name** - clean, not embedded in title
3. **Album name** - that exists in music databases

Playlist tracks only have #2 (from `channel` field). Without a real album name, beets cannot match.

---

## Part 4: Solution - Playlist as Pseudo-Album

### Approach

Treat playlists as "virtual albums" using playlist-level metadata:

```python
# yt-dlp metadata mapping for playlists
album = playlist_title      # e.g., "Trending 20 Spain"
artist = channel            # e.g., "Bizarrap"
track = playlist_index      # e.g., 1, 2, 3...
artwork = playlist_thumbnail
```

### Resulting File Structure
```
Playlists/
└── Trending 20 Spain/
    ├── 01 - J BALVIN - BZRP Music Sessions.opus
    ├── 02 - ROSALÍA - La Perla.opus
    └── 03 - La Oreja de Van Gogh - Todos Estamos Bailando.opus
```

### Embedded Metadata
```
title:  J BALVIN || BZRP Music Sessions #62/66
artist: Bizarrap
album:  Trending 20 Spain
track:  1
```

### POC Verification
```python
# Test download with playlist metadata
ydl_opts = {
    'postprocessors': [
        {
            'key': 'MetadataParser',
            'when': 'pre_process',
            'actions': [
                (Actions.INTERPRET, 'playlist_title', '%(meta_album)s'),
                (Actions.INTERPRET, 'channel', '%(meta_artist)s'),
                (Actions.INTERPRET, 'playlist_index', '%(meta_track)s'),
            ],
        },
        {'key': 'FFmpegMetadata', 'add_metadata': True},
        {'key': 'EmbedThumbnail'},
    ],
}
```

**Result:** Successfully embedded metadata with `album: Trending 20 Spain`

---

## Part 5: Implementation Plan

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Folder organization | `Playlists/{playlist_title}/` | Keeps playlists together, separate from albums |
| Metadata source | yt-dlp only | Beets can't match playlist tracks |
| Album field | playlist_title | Creates pseudo-album for music players |
| Artist field | channel | Most reliable source |
| Artwork | Playlist thumbnail | Consistent for all tracks |
| Beets usage | Skip entirely | Tested - both album and singleton modes fail |
| Detection | User toggle in UI | Always ask, don't auto-detect |

### Files to Modify

| File | Changes |
|------|---------|
| `yubal/core/enums.py` | Add `ImportType` enum (ALBUM, PLAYLIST) |
| `yubal/core/models.py` | Add `import_type` to `AlbumInfo` and `Job` |
| `yubal/schemas/jobs.py` | Add `import_type` to request schema |
| `yubal/api/routes/jobs.py` | Accept and pass `import_type` |
| `yubal/services/downloader.py` | Add playlist-specific postprocessors |
| `yubal/services/sync.py` | Branch logic for album vs playlist |
| `web/src/...` | Add import type toggle |

### Implementation Steps

1. **Domain Model Updates**
   - Add `ImportType` enum to `enums.py`
   - Add `import_type` field to models

2. **API Updates**
   - Add `import_type` to job creation schema
   - Pass through to sync service

3. **Downloader Updates**
   - Add `_get_playlist_postprocessors()` method
   - Embed playlist metadata (title, channel, index)

4. **Sync Service Updates**
   - Branch on `import_type`
   - For playlists: download → organize (skip beets)
   - For albums: existing flow (download → beets)

5. **File Organization**
   - Create `Playlists/{playlist_title}/` directory
   - Move files directly (no beets involvement)

6. **Frontend Updates**
   - Add toggle for import type
   - Show auto-detected type but allow override

---

## Part 6: Limitations & Considerations

### Year/Date Reliability
- Album tracks: `release_date` = actual album release
- Playlist tracks: `release_date` = video upload date
- For playlist tracks, the year may not reflect the original song release

### Title Noise
- Playlist track titles contain "(Official Video)", "ft.", etc.
- No reliable way to clean without regex heuristics
- Accepted as trade-off for simplicity

### Album Hints in Description
- Some tracks have album name in description (e.g., "'LUX' Out Now")
- Only ~20% of tracks have this
- Not reliable enough to use programmatically

### Genre Information
- Skipping beets means no LastFM genre lookup
- Tracks will have YouTube's generic "Music" genre
- Acceptable trade-off for reliability

---

## Part 7: Test Cases

### Integration Test URLs

```python
# Album test (existing flow should still work)
album_url = "https://music.youtube.com/playlist?list=OLAK5uy_kqKSSUvhqlZJQUlvZzxdhm4fXg7mLtpVQ"

# Playlist test (new flow)
playlist_url = "https://music.youtube.com/playlist?list=OLAK5uy_mzYnlaHgFOvLaxqIPnnouEr-idiUn4NIM"
```

### Expected Results

**Album Import:**
```
data/
└── ROSALIA/
    └── 2025 - LUX/
        ├── 01 - Sexo, Violencia y Llantas.opus
        ├── 02 - ...
        └── (beets-enriched metadata)
```

**Playlist Import:**
```
data/
└── Playlists/
    └── Trending 20 Spain/
        ├── 01 - Bizarrap - J BALVIN __ BZRP Music Sessions.opus
        ├── 02 - ROSALÍA - La Perla (Official Video).opus
        └── (yt-dlp metadata only)
```

---

## Appendix: yt-dlp Postprocessor Configuration

```python
# For albums (existing)
def _get_album_postprocessors(self):
    return [
        {'key': 'FFmpegExtractAudio', ...},
        {
            'key': 'MetadataParser',
            'when': 'pre_process',
            'actions': [
                (Actions.INTERPRET, 'playlist_index', '%(meta_track)s'),
                (Actions.INTERPRET, 'release_date', '%(meta_date)s'),
                (Actions.INTERPRET, '%(artists.0)s', '%(meta_artist)s'),
            ],
        },
        {'key': 'FFmpegMetadata', 'add_metadata': True},
        {'key': 'EmbedThumbnail'},
    ]

# For playlists (new)
def _get_playlist_postprocessors(self):
    return [
        {'key': 'FFmpegExtractAudio', ...},
        {
            'key': 'MetadataParser',
            'when': 'pre_process',
            'actions': [
                (Actions.INTERPRET, 'playlist_title', '%(meta_album)s'),
                (Actions.INTERPRET, 'channel', '%(meta_artist)s'),
                (Actions.INTERPRET, 'playlist_index', '%(meta_track)s'),
            ],
        },
        {'key': 'FFmpegMetadata', 'add_metadata': True},
        {'key': 'EmbedThumbnail'},
    ]
```
