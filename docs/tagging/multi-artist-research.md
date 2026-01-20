# Multi-Artist Tagging Research

Research conducted on Plex, Jellyfin, and Navidrome multi-artist handling.

---

## Overview of Tagging Approaches

| Approach | Example | Description |
|----------|---------|-------------|
| **Delimiter in ARTIST** | `ARTIST=Alice / Bob` | Single tag value, parsed by player |
| **Multi-value ARTIST** | `ARTIST=Alice` + `ARTIST=Bob` | Same key repeated with multiple entries |
| **Multi-value ARTISTS** | `ARTISTS=Alice` + `ARTISTS=Bob` | Plural tag (MusicBrainz convention), multiple entries |

---

## Format Capabilities (Independent of Player)

| Format | Delimiter ARTIST | Multi-value ARTIST | Multi-value ARTISTS |
|--------|------------------|--------------------|--------------------|
| **Opus** (Vorbis) | Yes | Yes (native) | Yes (native) |
| **MP3** (ID3v2.4) | Yes | Yes (null-byte separated) | Yes (null-byte separated) |
| **MP3** (ID3v2.3) | Yes | No | No |
| **M4A** (MP4) | Yes | No | No |

---

## Player Support Matrix

### Plex

| Format | Delimiter ARTIST | Multi-value ARTIST | Multi-value ARTISTS |
|--------|------------------|--------------------|--------------------|
| **Opus** | Metadata often unread | Metadata often unread | Ignored |
| **MP3** | Comma only | Works (FFmpeg patch) | Ignored |
| **M4A** | Comma only | Only last value kept | Ignored |

**Plex limitations:**
- Opus metadata reading is broken since 2016 ([source](https://forums.plex.tv/t/opus-metadata/170462))
- Ignores `ARTISTS`/`ALBUMARTISTS` tags entirely
- Database stores artists as text, not linked entities
- 10+ year feature request for proper multi-artist unaddressed ([source](https://forums.plex.tv/t/better-support-for-albums-and-tracks-with-multiple-artists/116658))

**Sources:**
- [Plex Adding Music From Folders](https://support.plex.tv/articles/200265296-adding-music-media-from-folders/)
- [Plex Embedded Metadata](https://support.plex.tv/articles/200381093-identifying-music-media-using-embedded-metadata/)
- [Multi-value tag parsing forum](https://forums.plex.tv/t/optimise-the-parse-of-multi-valued-tag-for-track-artist/914364)
- [Artist separators forum](https://forums.plex.tv/t/artist-seperators-in-plex-music/686301)

---

### Jellyfin

| Format | Delimiter ARTIST | Multi-value ARTIST | Multi-value ARTISTS |
|--------|------------------|--------------------|--------------------|
| **Opus** | Yes (default) | Works | Requires `PreferNonstandardArtistsTag=true` |
| **MP3** | Yes (default) | ID3v2.4 only | Requires setting + ID3v2.4 |
| **M4A** | Yes (default) | No | No |

**Jellyfin default delimiters:** `/`, `;`, `|`, `\`

**Jellyfin notes:**
- Most flexible delimiter support
- `ARTISTS` tag requires config flag to enable
- Good multi-value support for Opus and ID3v2.4

---

### Navidrome

| Format | Delimiter ARTIST | Multi-value ARTIST | Multi-value ARTISTS |
|--------|------------------|--------------------|--------------------|
| **Opus** | Yes (fallback) | Works | Preferred |
| **MP3** | Yes (fallback) | ID3v2.4 only | ID3v2.4 only |
| **M4A** | Yes (fallback) | No | Known issues |

**Navidrome default delimiters:** `/`, `;`, `feat.`, `ft.`

**Navidrome notes:**
- Prefers `ARTISTS` tag for explicit artist linking ([source](https://www.navidrome.org/docs/usage/library/tagging/))
- `ARTIST` used as display name when both exist
- Best native multi-artist support of the three
- M4A multi-value has known issues ([issue #3806](https://github.com/navidrome/navidrome/issues/3806))

---

## Delimiter Support by Player

| Delimiter | Plex | Jellyfin | Navidrome | Compatible With |
|-----------|------|----------|-----------|-----------------|
| `,` (comma) | Yes | No | No | Plex only |
| `;` (semicolon) | No | Yes | Yes | Jellyfin + Navidrome |
| `/` (slash) | No | Yes | Yes | Jellyfin + Navidrome |
| `\|` (pipe) | No | Yes | No | Jellyfin only |
| `\` (backslash) | No | Yes | No | Jellyfin only |
| `feat.` / `ft.` | No | No | Yes | Navidrome only |
| `&` | No | No | No | None |

**Critical conflict:** Plex uses comma, Jellyfin/Navidrome use slash/semicolon. No single delimiter works across all three by default.

---

## Consolidated Support Matrix (All Three Players)

### Opus

| Approach | Plex | Jellyfin | Navidrome | Universal? |
|----------|------|----------|-----------|------------|
| Delimiter `,` | Metadata issues | No | No | No |
| Delimiter `/` | Metadata issues | Yes | Yes | No |
| Multi-value ARTIST | Metadata issues | Yes | Yes | No |
| Multi-value ARTISTS | No | Config needed | Yes | No |

**Verdict:** Opus is problematic for Plex. Avoid if Plex is a target.

### MP3 (ID3v2.4)

| Approach | Plex | Jellyfin | Navidrome | Universal? |
|----------|------|----------|-----------|------------|
| Delimiter `,` | Yes | No | No | No |
| Delimiter `/` | No | Yes | Yes | No |
| Multi-value ARTIST | Yes | Yes | Yes | **Yes** |
| Multi-value ARTISTS | No | Config needed | Yes | No |

**Verdict:** Multi-value ARTIST works across all three for MP3 ID3v2.4.

### M4A

| Approach | Plex | Jellyfin | Navidrome | Universal? |
|----------|------|----------|-----------|------------|
| Delimiter `,` | Yes | No | No | No |
| Delimiter `/` | No | Yes | Yes | No |
| Multi-value ARTIST | No | No | No | No |
| Multi-value ARTISTS | No | No | No | No |

**Verdict:** No universal solution for M4A. Must use delimiter, but no single delimiter works everywhere.

---

## ARTIST vs ARTISTS Tag Clarification

### Multi-value ARTIST (native multi-value)

Native feature of certain tag formats where you repeat the same tag key:

```
# Vorbis comments (FLAC/Opus) - multiple ARTIST fields
ARTIST=Alice
ARTIST=Bob

# ID3v2.4 (MP3) - multiple TPE1 frames
TPE1=Alice
TPE1=Bob
```

### ARTISTS (MusicBrainz convention)

Separate tag name introduced by MusicBrainz Picard:

```
ARTIST=Alice & Bob        # Display string (how it appears)
ARTISTS=Alice             # Individual artist 1
ARTISTS=Bob               # Individual artist 2
```

### How Navidrome Uses Both

1. **If `ARTISTS` exists** (multi-value) -> Navidrome uses those values directly for artist linking
2. **If only `ARTIST` exists** -> Navidrome splits it using common delimiters
3. **If both exist** -> `ARTIST` = display name, `ARTISTS` = actual artist data

---

## Recommended Strategy by Target

### For Plex-only

```
ARTIST      = Alice, Bob        # Comma-separated
ALBUMARTIST = Alice, Bob        # Must match for album grouping
TITLE       = Song Name (feat. Guest)  # Featured artists in title
```

### For Navidrome-only

```
ARTIST       = Alice & Bob      # Display string
ARTISTS      = Alice            # Multi-value entry 1
ARTISTS      = Bob              # Multi-value entry 2
ALBUMARTIST  = Alice & Bob      # Display string
ALBUMARTISTS = Alice            # Multi-value entry 1
ALBUMARTISTS = Bob              # Multi-value entry 2
```

### For Both Plex + Navidrome (Maximum Compatibility)

```
ARTIST       = Alice, Bob       # Comma-delimited (Plex reads this)
ARTISTS      = Alice            # Multi-value (Navidrome prefers this)
ARTISTS      = Bob
ALBUMARTIST  = Alice, Bob       # Comma-delimited
ALBUMARTISTS = Alice            # Multi-value
ALBUMARTISTS = Bob
```

---

## Delimiter Configuration Guide

### Recommended Defaults by Target

| Target Players | Recommended Delimiter | Rationale |
|----------------|----------------------|-----------|
| **Plex only** | `,` (comma) | Only delimiter Plex parses |
| **Jellyfin only** | `/` (slash) | Clean, widely supported |
| **Navidrome only** | `/` (slash) | Works; `ARTISTS` tag preferred anyway |
| **Jellyfin + Navidrome** | `/` (slash) | Works in both |
| **Plex + Jellyfin** | `,` (comma) | Plex needs comma; Jellyfin won't parse but displays correctly |
| **Plex + Navidrome** | `,` (comma) | Plex needs comma; Navidrome won't parse but displays correctly |
| **All three** | See dual-tag strategy | No single delimiter works |

### Delimiter Trade-offs

| Delimiter | Pros | Cons |
|-----------|------|------|
| `,` | Plex parses it | Jellyfin/Navidrome show as literal text |
| `/` | Jellyfin + Navidrome parse it | Plex shows as literal text; conflicts with AC/DC style names |
| `;` | Jellyfin + Navidrome parse it | Plex shows as literal text |

---

## What Each Configuration Achieves

### Delimiter = `,` (comma)

| Player | Parsing | Display | Artist Linking |
|--------|---------|---------|----------------|
| Plex | Split into artists | Alice, Bob | Separate entries |
| Jellyfin | Not parsed | "Alice, Bob" | Single combined artist |
| Navidrome | Not parsed | "Alice, Bob" | Single combined artist* |

*Navidrome will use `ARTISTS` tag if present, achieving proper linking despite delimiter not being parsed.

### Delimiter = `/` (slash)

| Player | Parsing | Display | Artist Linking |
|--------|---------|---------|----------------|
| Plex | Not parsed | "Alice / Bob" | Single combined artist |
| Jellyfin | Split into artists | Alice, Bob | Separate entries |
| Navidrome | Split into artists | Alice, Bob | Separate entries |

### Multi-value ARTIST (Opus/MP3)

| Player | Parsing | Display | Artist Linking |
|--------|---------|---------|----------------|
| Plex (MP3) | Reads all values | Alice, Bob | Works |
| Plex (Opus) | Metadata issues | - | May not work |
| Jellyfin | Reads all values | Alice, Bob | Works |
| Navidrome | Reads all values | Alice, Bob | Works |

---

## Format Recommendation for Multi-Server Compatibility

| Format | Plex | Navidrome | Jellyfin | Verdict |
|--------|------|-----------|----------|---------|
| **MP3** | Best support | Full support | Full support | **Recommended** |
| **M4A** | Good (single-value) | Multi-value issues | Delimiter only | Use single delimiter string |
| **Opus** | Metadata broken | Full support | Full support | Avoid if Plex needed |

---

## Summary: Best Approach by Target

| Target | Opus | MP3 | M4A |
|--------|------|-----|-----|
| **Plex only** | Avoid format | Multi-value `ARTIST` | Delimiter `,` |
| **Jellyfin only** | Multi-value `ARTIST` | Multi-value `ARTIST` or delimiter `/` | Delimiter `/` |
| **Navidrome only** | Multi-value `ARTISTS` | Multi-value `ARTISTS` | Delimiter `/` |
| **Jellyfin + Navidrome** | Multi-value `ARTIST` + `ARTISTS` | Multi-value `ARTIST` + `ARTISTS` | Delimiter `/` |
| **Plex + others** | Avoid format | Multi-value `ARTIST` + `ARTISTS` | Delimiter `,` (compromise) |
| **All three** | Avoid format | Multi-value `ARTIST` + `ARTISTS` | Delimiter `,` (Plex parses; others display as-is) |

---

## Key Takeaways

1. **MP3 with multi-value ARTIST is the only universal solution** across all three players
2. **M4A requires delimiter** - user should configure based on primary target
3. **Opus should be avoided if Plex is a target** - metadata reading is broken
4. **No single delimiter works everywhere:**
   - `,` -> Plex parses, others don't
   - `/` -> Jellyfin + Navidrome parse, Plex doesn't
5. **Always write `ARTISTS` tag for Navidrome** - it's their preferred method and works regardless of delimiter
6. **Default recommendation:** `/` delimiter if Plex not needed, `,` if Plex is a target
7. **Always set `ALBUMARTIST`** - all three players require it for proper album organization
8. **`Various Artists`** is a magic string recognized by all three for compilations
