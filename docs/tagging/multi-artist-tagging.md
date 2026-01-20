# Multi-Artist Tagging: Complete Analysis

## Plex vs Navidrome vs Jellyfin

This document analyzes how different media servers handle multiple artists in music files and provides recommendations for optimal tagging strategies.

---

## Tagging Approach Support Matrix

| Approach | Plex | Navidrome | Jellyfin |
|----------|------|-----------|----------|
| `ARTIST` with delimiter | Comma only | `, ; / feat. ft.` | `/ ; \| \` |
| Multiple `ARTIST` tags (multi-value) | MP3 only | Full support | Full support |
| Multiple `ARTISTS` tags (MusicBrainz) | Ignored | Preferred | Requires setting |

---

## Delimiter Recognition

| Delimiter | Plex | Navidrome | Jellyfin | Yubal Config |
|-----------|------|-----------|----------|--------------|
| `,` (comma) | Yes | Yes | No | `--delimiter ","` |
| `;` (semicolon) | No | Yes | Yes | `--delimiter ";"` |
| `/` (slash) | No | Yes | Yes | `--delimiter "/"` |
| `\|` (pipe) | No | No | Yes | `--delimiter "\|"` |

### Recommended Delimiter by Target

| Target Server(s) | Recommended Delimiter |
|------------------|----------------------|
| Plex | `,` (comma) - only option |
| Navidrome | `/` or `;` |
| Jellyfin | `/` or `;` |
| Navidrome + Jellyfin | `/` (works in both) |
| Plex + Navidrome | `,` (only common delimiter) |
| Plex + Jellyfin | No common delimiter* |
| All three | No common delimiter* |

\* Use `ARTIST` + `ARTISTS` dual-tag strategy (see below)

---

## Format-Specific Support

### MP3 (ID3v2.3/v2.4)

| Tagging Method | Plex | Navidrome | Jellyfin |
|----------------|------|-----------|----------|
| Delimiter in `ARTIST` | Comma only | Multiple | Multiple |
| Multiple `TPE1` frames (ID3v2.4) | Works | Works | Works |
| `ARTISTS` tag (TXXX frame) | Ignored | Preferred | Requires setting |

### M4A (MP4/AAC)

| Tagging Method | Plex | Navidrome | Jellyfin |
|----------------|------|-----------|----------|
| Delimiter in `ARTIST` | Comma only | Multiple | Multiple |
| Multiple `©ART` atoms | Last value only | [Issue #3806](https://github.com/navidrome/navidrome/issues/3806) | Not supported |
| `ARTISTS` tag | Ignored | May not read | Requires setting |

### Opus (Vorbis Comments)

| Tagging Method | Plex | Navidrome | Jellyfin |
|----------------|------|-----------|----------|
| Delimiter in `ARTIST` | Often unread | Multiple | Multiple |
| Multiple `ARTIST` fields | Often unread | Works | Works |
| Multiple `ARTISTS` fields | Ignored | Preferred | Requires setting |

> **Plex + Opus Warning**: Plex has had [metadata issues with Opus](https://forums.plex.tv/t/opus-metadata/170462) since 2016. Files may appear as `[unknown artist]`.

---

## Format Recommendation

| Format | Plex | Navidrome | Jellyfin | Verdict |
|--------|------|-----------|----------|---------|
| **MP3** | Best | Full | Full | **Best multi-server** |
| **M4A** | Good | Multi-value issues | Delimiter only | Delimiter string only |
| **Opus** | Broken | Best | Best | Avoid if Plex needed |

---

## Tagging Strategies by Target

### Single Server

| Target | Strategy |
|--------|----------|
| **Plex** | Delimiter `,` in `ARTIST` |
| **Navidrome** | Multi-value `ARTISTS` (preferred) or delimiter `/` in `ARTIST` |
| **Jellyfin** | Multi-value `ARTIST` (Opus) or delimiter `/` in `ARTIST` |

### Navidrome + Jellyfin (No Plex)

**Simplest approach** - works without any server settings:

```
ARTIST      = Artist1 / Artist2    # Delimiter (configurable)
ALBUMARTIST = Artist1 / Artist2
```

**Best approach** (Opus only):

```
ARTIST      = Artist1              # Multi-value
ARTIST      = Artist2
ALBUMARTIST = Artist1
ALBUMARTIST = Artist2
```

### All Three Servers (Maximum Compatibility)

No single delimiter works everywhere. Use **dual-tag strategy**:

```
ARTIST       = Artist1, Artist2    # Comma for Plex
ARTISTS      = Artist1             # Multi-value for Navidrome
ARTISTS      = Artist2
ALBUMARTIST  = Artist1, Artist2    # Comma for Plex
ALBUMARTISTS = Artist1             # Multi-value for Navidrome
ALBUMARTISTS = Artist2
```

> Jellyfin users need `PreferNonstandardArtistsTag=true` to read `ARTISTS`

---

## Yubal Configuration Guide

### Delimiter Setting

| User's Server | Yubal Delimiter Setting |
|---------------|------------------------|
| Plex | `,` |
| Navidrome | `/` or `;` |
| Jellyfin | `/` or `;` |
| Navidrome + Jellyfin | `/` |
| Includes Plex | `,` + enable dual-tag mode |

### Dual-Tag Mode

When enabled, yubal writes **both**:
- `ARTIST` with configured delimiter (for Plex/display)
- `ARTISTS` as multi-value (for Navidrome/Jellyfin)

| Setting | Single-Tag Mode | Dual-Tag Mode |
|---------|-----------------|---------------|
| `ARTIST` | `A, B` (delimiter) | `A, B` (delimiter) |
| `ARTISTS` | Not written | `A` + `B` (multi-value) |

---

## Quick Reference

### Tags Written

| Tag | Value | When |
|-----|-------|------|
| `ARTIST` | Delimiter-joined string | Always |
| `ARTISTS` | Multi-value entries | Dual-tag mode only |
| `ALBUMARTIST` | Delimiter-joined or single | Always |
| `ALBUMARTISTS` | Multi-value entries | Dual-tag mode only |
| `TITLE` | `Song (feat. X)` | If featured artist |

### Recommended Defaults

| Setting | Default | Reason |
|---------|---------|--------|
| Delimiter | `/` | Works in Navidrome + Jellyfin |
| Dual-tag mode | Off | Only needed if Plex user |

### Rules

1. **Always set `ALBUMARTIST`** - all players need it
2. **`Various Artists`** is magic string for compilations
3. **Opus**: Best for Navidrome/Jellyfin, avoid for Plex
4. **M4A**: Delimiter only, no multi-value support
5. **MP3**: Works everywhere, safest choice

---

## Implementation Reference

```python
def write_artist_tags(
    audio,
    artists: list[str],
    format: str,
    delimiter: str = " / ",
    dual_tag_mode: bool = False
):
    """Write artist tags with configurable delimiter."""

    joined = delimiter.join(artists)

    if format == "opus":
        audio["ARTIST"] = [joined]
        if dual_tag_mode:
            audio["ARTISTS"] = artists

    elif format == "mp3":
        from mutagen.id3 import TPE1, TXXX
        audio["TPE1"] = TPE1(encoding=3, text=[joined])
        if dual_tag_mode:
            audio["TXXX:ARTISTS"] = TXXX(encoding=3, desc="ARTISTS", text=artists)

    elif format == "m4a":
        audio["©ART"] = [joined]
        # No multi-value support for M4A
```

---

## User Decision Flowchart

```
Which server(s) do you use?
│
├── Plex only
│   └── Delimiter: ","
│
├── Navidrome only
│   └── Delimiter: "/" (or multi-value ARTISTS)
│
├── Jellyfin only
│   └── Delimiter: "/"
│
├── Navidrome + Jellyfin
│   └── Delimiter: "/"
│
├── Plex + Navidrome
│   └── Delimiter: "," + Dual-tag mode ON
│
├── Plex + Jellyfin
│   └── Delimiter: "," + Dual-tag mode ON
│       (Jellyfin needs PreferNonstandardArtistsTag)
│
└── All three
    └── Delimiter: "," + Dual-tag mode ON
        (Jellyfin needs PreferNonstandardArtistsTag)
```

---

## Server-Specific Notes

### Jellyfin

- Uses ATL (Audio Tag Library) for metadata extraction
- Default delimiters: `/ ; | \`
- Built-in whitelist for bands like `AC/DC`, `K/DA`, `LOONA 1/3`
- Custom delimiters configurable via library settings
- `PreferNonstandardArtistsTag` setting enables `ARTISTS` tag reading

Key files in Jellyfin codebase:
- `MediaBrowser.Providers/MediaInfo/AudioFileProber.cs` - Main tag reading
- `MediaBrowser.MediaEncoding/Probing/ProbeResultNormalizer.cs` - Delimiter parsing
- `MediaBrowser.Model/Configuration/LibraryOptions.cs` - Settings

### Navidrome

- Prefers `ARTISTS` (plural) tag for multi-value
- Falls back to delimiter parsing in `ARTIST` tag
- Supports `, ; / feat. ft.` as delimiters
- Full Vorbis multi-value support

### Plex

- Only recognizes comma (`,`) as delimiter
- Ignores `ARTISTS` tag entirely
- Known issues with Opus metadata since 2016
- Best support for MP3 format
