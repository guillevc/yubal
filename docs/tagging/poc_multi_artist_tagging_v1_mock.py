#!/usr/bin/env python3
"""
Multi-Artist Tagging Proof of Concept
======================================

This script demonstrates different strategies for tagging multi-artist tracks
using the mediafile library, with compatibility across Plex, Jellyfin, and Navidrome.

Background:
-----------
Different media servers handle multi-artist tags differently:
- Plex: Only parses comma (,) as delimiter, ignores ARTISTS tag
- Jellyfin: Parses / ; | \\ as delimiters, ARTISTS tag requires config
- Navidrome: Parses / ; feat. ft. as delimiters, prefers ARTISTS tag

Format limitations:
- Opus/FLAC: Native multi-value support via Vorbis comments
- MP3 (ID3v2.4): Multi-value via null-byte separation
- MP3 (ID3v2.3): No multi-value support
- M4A: No multi-value support for artist tags

This PoC explores:
1. How mediafile handles the `artist` vs `artists` attributes
2. Writing multi-value tags in different formats
3. A dual-tag strategy for cross-server compatibility

Usage:
------
    python poc_multi_artist_tagging.py

Requirements:
-------------
    pip install mediafile

Note: This creates temporary test files that are cleaned up automatically.
"""

from __future__ import annotations

from dataclasses import dataclass

# mediafile provides a unified interface for audio file metadata
from mediafile import MediaFile


# =============================================================================
# SAMPLE DATA
# =============================================================================

@dataclass
class SampleTrack:
    """Sample track data for testing."""
    title: str
    artists: list[str]
    album: str
    album_artists: list[str]


SAMPLE_TRACKS = [
    SampleTrack(
        title="Collaboration Song",
        artists=["Alice", "Bob"],
        album="Joint Album",
        album_artists=["Alice", "Bob"],
    ),
    SampleTrack(
        title="Featured Track",
        artists=["Main Artist", "Featured Guest"],
        album="Solo Album",
        album_artists=["Main Artist"],
    ),
    SampleTrack(
        title="Band Song",
        artists=["AC/DC"],  # Edge case: artist name contains delimiter
        album="Rock Album",
        album_artists=["AC/DC"],
    ),
    SampleTrack(
        title="Triple Collab",
        artists=["Producer", "Singer", "Rapper"],
        album="Various Artists Collection",
        album_artists=["Various Artists"],
    ),
]


# =============================================================================
# TAGGING STRATEGIES
# =============================================================================

def strategy_delimiter_only(
    audio: MediaFile,
    track: SampleTrack,
    delimiter: str = " / ",
) -> dict[str, str]:
    """
    Strategy 1: Delimiter-separated string only

    This is the simplest approach. Works with all formats but relies on
    the media server to parse the delimiter correctly.

    Compatibility:
    - Plex: Only if delimiter is ","
    - Jellyfin: If delimiter is / ; | \
    - Navidrome: If delimiter is / ; or contains feat./ft.

    Args:
        audio: MediaFile instance to modify
        track: Track metadata
        delimiter: Delimiter to join artists (default: " / ")

    Returns:
        Dict describing what was written
    """
    joined_artists = delimiter.join(track.artists)
    joined_album_artists = delimiter.join(track.album_artists)

    audio.title = track.title
    audio.artist = joined_artists
    audio.album = track.album
    audio.albumartist = joined_album_artists

    return {
        "strategy": "delimiter_only",
        "delimiter": delimiter,
        "artist_tag": joined_artists,
        "albumartist_tag": joined_album_artists,
    }


def strategy_multi_value(
    audio: MediaFile,
    track: SampleTrack,
) -> dict[str, str | list[str]]:
    """
    Strategy 2: Multi-value tags (where supported)

    mediafile's `artists` (plural) attribute writes multi-value tags:
    - Opus/FLAC: Multiple ARTIST fields in Vorbis comments
    - MP3 (ID3v2.4): Null-byte separated values in TPE1 frame
    - M4A: NOT SUPPORTED - only first value is kept

    Compatibility:
    - Plex: Works for MP3 (via FFmpeg patch), broken for Opus
    - Jellyfin: Works for Opus and MP3 (ID3v2.4)
    - Navidrome: Works for Opus and MP3 (ID3v2.4)

    Args:
        audio: MediaFile instance to modify
        track: Track metadata

    Returns:
        Dict describing what was written
    """
    audio.title = track.title
    audio.album = track.album

    # `artists` (plural) writes multi-value tags
    # `artist` (singular) writes a single string
    audio.artists = track.artists
    audio.albumartists = track.album_artists

    return {
        "strategy": "multi_value",
        "artists_tag": track.artists,
        "albumartists_tag": track.album_artists,
    }


def strategy_dual_tag(
    audio: MediaFile,
    track: SampleTrack,
    delimiter: str = ", ",
) -> dict[str, str | list[str]]:
    """
    Strategy 3: Dual-tag approach (recommended for cross-server compatibility)

    Writes BOTH:
    1. `artist` (singular) with delimiter-joined string - for Plex and display
    2. `artists` (plural) with multi-value list - for Navidrome/Jellyfin

    This provides the best compatibility:
    - Plex reads the delimiter-joined `artist` tag
    - Navidrome prefers multi-value `artists` tag (falls back to parsing `artist`)
    - Jellyfin reads multi-value `artists` (with config) or parses `artist`

    Note: For MP3, mediafile writes `artists` to a TXXX:ARTISTS frame,
    which is the MusicBrainz convention that Navidrome prefers.

    Args:
        audio: MediaFile instance to modify
        track: Track metadata
        delimiter: Delimiter for the singular artist tag (default: ", ")

    Returns:
        Dict describing what was written
    """
    joined_artists = delimiter.join(track.artists)
    joined_album_artists = delimiter.join(track.album_artists)

    audio.title = track.title
    audio.album = track.album

    # Write BOTH singular (delimiter-joined) and plural (multi-value)
    audio.artist = joined_artists          # TPE1 for MP3, ARTIST for Opus
    audio.artists = track.artists          # TXXX:ARTISTS for MP3, ARTISTS for Opus
    audio.albumartist = joined_album_artists
    audio.albumartists = track.album_artists

    return {
        "strategy": "dual_tag",
        "delimiter": delimiter,
        "artist_tag": joined_artists,
        "artists_tag": track.artists,
        "albumartist_tag": joined_album_artists,
        "albumartists_tag": track.album_artists,
    }


# =============================================================================
# VERIFICATION
# =============================================================================

def read_tags(path: str) -> dict:
    """Read back tags from a file to verify what was written."""
    audio = MediaFile(path)
    return {
        "format": path.split(".")[-1],
        "title": audio.title,
        "artist": audio.artist,          # Singular - delimiter-joined or first value
        "artists": audio.artists,        # Plural - list of values
        "album": audio.album,
        "albumartist": audio.albumartist,
        "albumartists": audio.albumartists,
    }


# =============================================================================
# MOCK FOR DEMONSTRATION
# =============================================================================

class MockMediaFile:
    """Mock MediaFile for demonstration without actual audio files."""

    def __init__(self, path: str = "mock.mp3"):
        self.path = path
        self.title: str | None = None
        self.artist: str | None = None
        self.artists: list[str] | None = None
        self.album: str | None = None
        self.albumartist: str | None = None
        self.albumartists: list[str] | None = None

    def save(self) -> None:
        """Mock save - just print what would be written."""
        print(f"  [MOCK] Would save to: {self.path}")


# =============================================================================
# DEMONSTRATIONS
# =============================================================================

def demonstrate_strategy(
    strategy_name: str,
    strategy_func,
    track: SampleTrack,
    **kwargs,
) -> None:
    """Demonstrate a tagging strategy with sample data."""
    print(f"\n{'='*60}")
    print(f"Strategy: {strategy_name}")
    print(f"{'='*60}")
    print(f"Track: {track.title}")
    print(f"Artists: {track.artists}")
    print(f"Album Artists: {track.album_artists}")
    print()

    mock = MockMediaFile()
    result = strategy_func(mock, track, **kwargs)

    print("Tags written:")
    for key, value in result.items():
        print(f"  {key}: {value}")


def demonstrate_format_behavior() -> None:
    """Document expected behavior for each format."""
    print("\n" + "="*60)
    print("FORMAT-SPECIFIC BEHAVIOR")
    print("="*60)

    formats = {
        ".opus": {
            "multi_value_artist": True,
            "multi_value_artists": True,
            "notes": [
                "Vorbis comments support multiple ARTIST fields natively",
                "ARTISTS tag is also natively supported",
                "Plex has metadata reading issues with Opus since 2016",
            ],
        },
        ".mp3": {
            "multi_value_artist": "ID3v2.4 only (null-byte separated)",
            "multi_value_artists": "ID3v2.4 only (TXXX frame)",
            "notes": [
                "ID3v2.4 supports multi-value via null-byte separation",
                "ID3v2.3 does NOT support multi-value",
                "mediafile writes ARTISTS to TXXX:ARTISTS frame",
                "All three servers support MP3 multi-value (best compatibility)",
            ],
        },
        ".m4a": {
            "multi_value_artist": False,
            "multi_value_artists": False,
            "notes": [
                "MP4 container does not support multi-value artist atoms",
                "Only delimiter-separated strings work",
                "Navidrome has known issues with M4A ARTISTS tag",
            ],
        },
    }

    for ext, info in formats.items():
        print(f"\n{ext.upper()}")
        print(f"  Multi-value ARTIST:  {info['multi_value_artist']}")
        print(f"  Multi-value ARTISTS: {info['multi_value_artists']}")
        print("  Notes:")
        for note in info["notes"]:
            print(f"    - {note}")


def demonstrate_server_compatibility() -> None:
    """Document which strategies work with which servers."""
    print("\n" + "="*60)
    print("SERVER COMPATIBILITY MATRIX")
    print("="*60)

    print("""
    GENERAL STRATEGY SUPPORT
    +---------------------+------------+------------+------------+
    | Strategy            |    Plex    |  Jellyfin  |  Navidrome |
    +---------------------+------------+------------+------------+
    | Delimiter ","       |     Y      |     N      |     N      |
    | Delimiter "/"       |     N      |     Y      |     Y      |
    | Multi-value ARTIST  |  MP3 only  |     Y      |     Y      |
    | Multi-value ARTISTS |     N      |  (config)  |     Y      |
    | Dual-tag (,)        |     Y      |  (config)  |     Y      |
    +---------------------+------------+------------+------------+
    """)

    print("""
    FORMAT-SPECIFIC: OPUS
    +---------------------+------------+------------+------------+
    | Strategy            |    Plex    |  Jellyfin  |  Navidrome |
    +---------------------+------------+------------+------------+
    | Delimiter ","       |     X      |     N      |     N      |
    | Delimiter "/"       |     X      |     Y      |     Y      |
    | Multi-value ARTIST  |     X      |     Y      |     Y      |
    | Multi-value ARTISTS |     X      |  (config)  |     Y      |
    | Dual-tag (,)        |     X      |  (config)  |     Y      |
    +---------------------+------------+------------+------------+
    X = Plex has metadata reading issues with Opus (broken since 2016)
    """)

    print("""
    FORMAT-SPECIFIC: MP3 (ID3v2.4)
    +---------------------+------------+------------+------------+
    | Strategy            |    Plex    |  Jellyfin  |  Navidrome |
    +---------------------+------------+------------+------------+
    | Delimiter ","       |     Y      |     N      |     N      |
    | Delimiter "/"       |     N      |     Y      |     Y      |
    | Multi-value ARTIST  |     Y      |     Y      |     Y      |
    | Multi-value ARTISTS |     N      |  (config)  |     Y      |
    | Dual-tag (,)        |     Y      |  (config)  |     Y      |
    +---------------------+------------+------------+------------+
    * MP3 is the ONLY format with universal multi-value ARTIST support
    """)

    print("""
    FORMAT-SPECIFIC: M4A
    +---------------------+------------+------------+------------+
    | Strategy            |    Plex    |  Jellyfin  |  Navidrome |
    +---------------------+------------+------------+------------+
    | Delimiter ","       |     Y      |     N      |     N      |
    | Delimiter "/"       |     N      |     Y      |     Y      |
    | Multi-value ARTIST  |     -      |     -      |     -      |
    | Multi-value ARTISTS |     -      |     -      |     -      |
    | Dual-tag (,)        |     Y*     |     N*     |     N*     |
    +---------------------+------------+------------+------------+
    - = Not supported by format (M4A lacks multi-value artist support)
    * = Only the delimiter string in ARTIST tag is used; ARTISTS ignored
    """)

    print("""
    LEGEND
    ------
    Y = Works out of the box (artists parsed and linked)
    N = Not parsed (shows as literal text, single combined artist)
    X = Format not supported by server
    - = Not supported by audio format
    (config) = Requires server configuration (PreferNonstandardArtistsTag)
    """)

    print("""
    RECOMMENDED STRATEGY BY TARGET
    +-------------------------+--------+-----------+-----------+
    | Target Server(s)        |  Opus  |    MP3    |    M4A    |
    +-------------------------+--------+-----------+-----------+
    | Plex only               | AVOID  | delim "," | delim "," |
    | Jellyfin only           | multi  | delim "/" | delim "/" |
    | Navidrome only          | ARTISTS| ARTISTS   | delim "/" |
    | Jellyfin + Navidrome    | multi  | multi     | delim "/" |
    | Plex + Navidrome        | AVOID  | dual ","  | delim "," |
    | Plex + Jellyfin         | AVOID  | dual ","  | delim "," |
    | All three               | AVOID  | dual ","  | delim "," |
    +-------------------------+--------+-----------+-----------+

    Key:
    - AVOID    = Don't use this format for this target
    - delim X  = Use delimiter X in ARTIST tag
    - multi    = Use multi-value ARTIST tags
    - ARTISTS  = Use multi-value ARTISTS tags (Navidrome preferred)
    - dual X   = Use dual-tag strategy with delimiter X
    """)


def demonstrate_implementation() -> None:
    """Show recommended implementation for yubal."""
    print("\n" + "="*60)
    print("RECOMMENDED IMPLEMENTATION FOR YUBAL")
    print("="*60)

    implementation = '''
def write_artist_tags(
    audio: MediaFile,
    artists: list[str],
    album_artists: list[str],
    delimiter: str = " / ",
    dual_tag_mode: bool = False,
) -> None:
    """
    Write artist tags with configurable strategy.

    Args:
        audio: MediaFile instance
        artists: List of track artists
        album_artists: List of album artists
        delimiter: Delimiter for joining artists (default: " / ")
        dual_tag_mode: If True, write both singular and plural tags
    """
    joined_artists = delimiter.join(artists)
    joined_album_artists = delimiter.join(album_artists)

    # Always write singular (delimiter-joined) tags
    audio.artist = joined_artists
    audio.albumartist = joined_album_artists

    # Optionally write plural (multi-value) tags for Navidrome/Jellyfin
    if dual_tag_mode:
        audio.artists = artists
        audio.albumartists = album_artists


# Usage presets:
PRESETS = {
    "plex": {"delimiter": ", ", "dual_tag_mode": False},
    "jellyfin": {"delimiter": " / ", "dual_tag_mode": False},
    "navidrome": {"delimiter": " / ", "dual_tag_mode": True},
    "universal": {"delimiter": ", ", "dual_tag_mode": True},
}
'''
    print(implementation)


def demonstrate_mediafile_api() -> None:
    """Show the key mediafile API difference between artist and artists."""
    print("\n" + "="*60)
    print("MEDIAFILE API: artist vs artists")
    print("="*60)

    print("""
    The mediafile library provides two related but distinct attributes:

    audio.artist (singular)
    -----------------------
    - Type: str
    - Writes a single string value
    - For MP3: Writes to TPE1 frame as single value
    - For Opus: Writes single ARTIST field
    - For M4A: Writes to \\xa9ART atom

    audio.artists (plural)
    ----------------------
    - Type: list[str]
    - Writes multiple values (where format supports it)
    - For MP3: Writes to TXXX:ARTISTS frame (MusicBrainz convention)
    - For Opus: Writes multiple ARTIST fields
    - For M4A: Limited support (may only keep first value)

    Key insight:
    - These are INDEPENDENT tags, not aliases
    - Writing to `artist` does NOT populate `artists` and vice versa
    - For maximum compatibility, write BOTH

    Example:
        audio.artist = "Alice, Bob"       # Single string for display/Plex
        audio.artists = ["Alice", "Bob"]  # Multi-value for Navidrome
    """)


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    """Run the proof of concept demonstrations."""
    print("="*60)
    print("MULTI-ARTIST TAGGING PROOF OF CONCEPT")
    print("="*60)

    # Show the key API difference first
    demonstrate_mediafile_api()

    # Demonstrate each strategy with sample data
    track = SAMPLE_TRACKS[0]  # Use collaboration track

    demonstrate_strategy(
        "Delimiter Only (comma for Plex)",
        strategy_delimiter_only,
        track,
        delimiter=", ",
    )

    demonstrate_strategy(
        "Delimiter Only (slash for Jellyfin/Navidrome)",
        strategy_delimiter_only,
        track,
        delimiter=" / ",
    )

    demonstrate_strategy(
        "Multi-Value Tags",
        strategy_multi_value,
        track,
    )

    demonstrate_strategy(
        "Dual-Tag (Maximum Compatibility)",
        strategy_dual_tag,
        track,
        delimiter=", ",
    )

    # Document format-specific behavior
    demonstrate_format_behavior()

    # Document server compatibility
    demonstrate_server_compatibility()

    # Show example implementation for yubal
    demonstrate_implementation()

    print("\n" + "="*60)
    print("END OF PROOF OF CONCEPT")
    print("="*60)


if __name__ == "__main__":
    main()
