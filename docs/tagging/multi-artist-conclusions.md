# Multi-Artist Tagging: Conclusions

This document synthesizes findings from research on Plex, Jellyfin, and Navidrome multi-artist handling.

---

## Executive Summary

**The core problem:** No single tagging approach works perfectly across all three media servers. Each server has different delimiter support, different tag preferences, and different format limitations.

**The solution:** A configurable dual-tag strategy that writes both delimiter-separated `ARTIST` tags and multi-value `ARTISTS` tags, allowing users to optimize for their specific server combination.

---

## Key Findings

### 1. Delimiter Incompatibility

| Delimiter | Plex | Jellyfin | Navidrome |
|-----------|------|----------|-----------|
| `,` (comma) | **Yes** | No | No |
| `;` (semicolon) | No | **Yes** | **Yes** |
| `/` (slash) | No | **Yes** | **Yes** |

**Conclusion:** There is no universal delimiter. Plex is the outlier, only supporting comma.

### 2. Multi-Value Tag Support

| Tag Type | Plex | Jellyfin | Navidrome |
|----------|------|----------|-----------|
| Multi-value `ARTIST` | MP3 only | Yes | Yes |
| Multi-value `ARTISTS` | **Ignored** | Requires config | **Preferred** |

**Conclusion:** `ARTISTS` (plural) is the best path forward for Navidrome/Jellyfin, but Plex ignores it entirely.

### 3. Format Limitations

| Format | Multi-value Support | Universal Solution? |
|--------|--------------------|--------------------|
| **MP3 (ID3v2.4)** | Yes | **Yes** - multi-value `ARTIST` works in all three |
| **M4A** | No | No - delimiter only, and no common delimiter exists |
| **Opus** | Yes | No - Plex has broken metadata support since 2016 |

**Conclusion:** MP3 is the only format with a universal multi-artist solution.

### 4. The "Various Artists" Convention

All three servers recognize `Various Artists` as a magic string for compilation albums. This is consistent across platforms.

---

## Discrepancies Found

### Delimiter Support in Navidrome

- **Research finding:** Navidrome does NOT parse comma as a delimiter by default
- **Clarification:** Navidrome's default delimiters are `/`, `;`, `feat.`, `ft.`
- **Impact:** Using comma for "Plex + Navidrome" means Navidrome won't parse it, but will display it correctly and can use `ARTISTS` tag as fallback

### Jellyfin ARTISTS Tag

- **Research finding:** Requires `PreferNonstandardArtistsTag=true` setting
- **Impact:** Users targeting Jellyfin with `ARTISTS` tags need server-side configuration

---

## Final Recommendations for yubal

### Default Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Default delimiter | `/` | Works in Jellyfin + Navidrome without config |
| Dual-tag mode | Off | Only enable if user has Plex |

### Format-Specific Strategy

| Format | Strategy |
|--------|----------|
| **Opus** | Write multi-value `ARTIST` + `ARTISTS`. Warn users about Plex incompatibility. |
| **MP3** | Write multi-value `ARTIST` + `ARTISTS` (ID3v2.4). This is the universal solution. |
| **M4A** | Write delimiter-separated `ARTIST` only. No multi-value support. |

### User Configuration Options

```
--delimiter "/"     # Default: works for Jellyfin + Navidrome
--delimiter ","     # For Plex users
--delimiter ";"     # Alternative for Jellyfin + Navidrome

--dual-tags         # Enable ARTISTS tag writing (for Navidrome)
--plex-mode         # Shortcut: sets delimiter="," and enables dual-tags
```

### Tags to Write

| Scenario | Tags Written |
|----------|-------------|
| **Standard** | `ARTIST` (delimiter-joined), `ALBUMARTIST` |
| **Dual-tag mode** | Above + `ARTISTS` (multi-value), `ALBUMARTISTS` (multi-value) |
| **Featured artist** | Move to `TITLE` as `(feat. X)` |

---

## Server Compatibility Matrix

### Optimal Configuration by Server Combination

| Target | Delimiter | Dual-Tags | Notes |
|--------|-----------|-----------|-------|
| Plex only | `,` | No | Simple comma separation |
| Jellyfin only | `/` | No | Delimiter parsing works |
| Navidrome only | `/` | Yes | `ARTISTS` tag preferred |
| Jellyfin + Navidrome | `/` | Yes | Best of both worlds |
| Plex + Navidrome | `,` | Yes | Plex parses comma; Navidrome uses `ARTISTS` |
| Plex + Jellyfin | `,` | Yes | Plex parses comma; Jellyfin needs config for `ARTISTS` |
| All three | `,` | Yes | Compromise: Plex parses, others use `ARTISTS` fallback |

### What Users Get

| Server | With `,` delimiter | With `/` delimiter | With `ARTISTS` tag |
|--------|-------------------|-------------------|-------------------|
| Plex | Parsed, linked artists | Literal text display | Ignored |
| Jellyfin | Literal text display | Parsed, linked artists | Linked (with config) |
| Navidrome | Literal text display | Parsed, linked artists | Linked (preferred) |

---

## Technical Implementation Summary

```python
def write_artist_tags(audio, artists: list[str], format: str, delimiter: str, dual_tags: bool):
    joined = delimiter.join(artists)

    if format == "opus":
        audio["ARTIST"] = [joined]          # Display string
        if dual_tags:
            audio["ARTISTS"] = artists      # Multi-value for Navidrome

    elif format == "mp3":
        audio["TPE1"] = TPE1(text=[joined])
        if dual_tags:
            audio["TXXX:ARTISTS"] = TXXX(desc="ARTISTS", text=artists)

    elif format == "m4a":
        audio["©ART"] = [joined]            # Delimiter only, no multi-value
```

---

## Open Questions

1. **Should yubal detect ID3 version?** ID3v2.3 doesn't support multi-value. Should we warn or auto-upgrade?

2. **Should yubal have server presets?** e.g., `--preset navidrome` sets optimal config automatically.

3. **How to handle artist names with delimiters?** e.g., "AC/DC" with `/` delimiter. Jellyfin has a whitelist; should yubal?

---

## Sources

### Plex
- [Adding Music From Folders](https://support.plex.tv/articles/200265296-adding-music-media-from-folders/)
- [Embedded Metadata](https://support.plex.tv/articles/200381093-identifying-music-media-using-embedded-metadata/)
- [Opus Metadata Issues (2016)](https://forums.plex.tv/t/opus-metadata/170462)
- [Multi-Artist Feature Request (10+ years)](https://forums.plex.tv/t/better-support-for-albums-and-tracks-with-multiple-artists/116658)
- [Multi-value Tag Parsing](https://forums.plex.tv/t/optimise-the-parse-of-multi-valued-tag-for-track-artist/914364)

### Navidrome
- [Tagging Guidelines](https://www.navidrome.org/docs/usage/library/tagging/)
- [M4A Multi-value Issue #3806](https://github.com/navidrome/navidrome/issues/3806)

### Jellyfin
- Source code: `MediaBrowser.Providers/MediaInfo/AudioFileProber.cs`
- Source code: `MediaBrowser.MediaEncoding/Probing/ProbeResultNormalizer.cs`
