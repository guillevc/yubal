#!/usr/bin/env python3
"""
Multi-Artist Tagging Proof of Concept (Final)
==============================================

This PoC demonstrates configurable multi-artist tagging with the mediafile
library for maximum compatibility across media servers:

- Plex: Only parses comma (,) as delimiter, ignores ARTISTS tag
- Jellyfin: Parses / ; | \\ as delimiters, ARTISTS tag requires config
- Navidrome: Parses / ; feat. ft. as delimiters, prefers ARTISTS tag

Format limitations:
- Opus: Native multi-value support via Vorbis comments
- MP3 (ID3v2.4): Multi-value via null-byte separation
- MP3 (ID3v2.3): No multi-value support
- M4A: No multi-value support for artist tags

This PoC:
1. Explains the mediafile `artist` vs `artists` API
2. Creates real audio files and tests tagging strategies
3. Shows a full compatibility matrix (servers x formats)
4. Provides server-specific configuration presets

Requirements:
    pip install mediafile
    ffmpeg (for creating test audio files)

Usage:
    python poc_multi_artist_tagging_final.py
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


# =============================================================================
# CONFIGURATION
# =============================================================================


class TargetServer(StrEnum):
    """Target media server presets."""

    PLEX = "plex"
    NAVIDROME = "navidrome"
    JELLYFIN = "jellyfin"
    NAVIDROME_JELLYFIN = "navidrome+jellyfin"
    ALL = "all"


@dataclass
class TaggingConfig:
    """Configuration for multi-artist tagging.

    Attributes:
        delimiter: String used to join multiple artists in ARTIST tag.
        write_artists_tag: If True, writes the non-standard ARTISTS tag.

    Server Compatibility:
        - Plex: Only reads comma-delimited ARTIST, ignores ARTISTS
        - Navidrome: Prefers ARTISTS, falls back to delimiter parsing
        - Jellyfin: Reads ARTIST with delimiters, ARTISTS requires setting
    """

    delimiter: str = " / "
    write_artists_tag: bool = False

    @classmethod
    def for_server(cls, server: TargetServer) -> TaggingConfig:
        """Get recommended config for target server(s).

        Delimiter choices:
        - Comma (,): Only works in Plex and Navidrome, NOT Jellyfin
        - Slash (/): Works in Navidrome and Jellyfin, NOT Plex
        - Semicolon (;): Works in Navidrome and Jellyfin, NOT Plex

        Dual-tag mode (write_artists_tag=True):
        - Writes ARTIST with delimiter (for Plex/display)
        - Writes ARTISTS as multi-value (for Navidrome/Jellyfin)
        """
        configs = {
            # Plex only: comma is the only recognized delimiter
            TargetServer.PLEX: cls(delimiter=", ", write_artists_tag=False),
            # Navidrome only: prefers ARTISTS tag
            TargetServer.NAVIDROME: cls(delimiter=" / ", write_artists_tag=True),
            # Jellyfin only: slash delimiter works out of the box
            TargetServer.JELLYFIN: cls(delimiter=" / ", write_artists_tag=False),
            # Navidrome + Jellyfin: slash works in both
            TargetServer.NAVIDROME_JELLYFIN: cls(delimiter=" / ", write_artists_tag=True),
            # All servers: comma for Plex + ARTISTS for Navidrome/Jellyfin
            TargetServer.ALL: cls(delimiter=", ", write_artists_tag=True),
        }
        return configs[server]


# =============================================================================
# SAMPLE DATA
# =============================================================================


@dataclass
class SampleTrack:
    """Sample track metadata for testing."""

    title: str
    artists: list[str]
    album: str
    album_artists: list[str]
    year: int = 2024
    track_number: int = 1
    total_tracks: int = 10


SAMPLE_TRACKS = [
    SampleTrack(
        title="Single Artist Track",
        artists=["Taylor Swift"],
        album="Midnights",
        album_artists=["Taylor Swift"],
    ),
    SampleTrack(
        title="Collaboration Track",
        artists=["Post Malone", "Morgan Wallen"],
        album="F-1 Trillion",
        album_artists=["Post Malone"],
        track_number=2,
    ),
    SampleTrack(
        title="Triple Collab",
        artists=["Major Lazer", "DJ Snake", "MO"],
        album="Peace Is The Mission",
        album_artists=["Major Lazer"],
        track_number=3,
    ),
    SampleTrack(
        title="Problematic Band Name",
        artists=["AC/DC"],  # Contains delimiter - should NOT be split!
        album="Back in Black",
        album_artists=["AC/DC"],
        track_number=4,
    ),
    SampleTrack(
        title="Compilation Track",
        artists=["Daft Punk", "Pharrell Williams", "Nile Rodgers"],
        album="Various Artists Compilation",
        album_artists=["Various Artists"],  # Magic string for compilations
        track_number=5,
    ),
]


# =============================================================================
# TAGGING IMPLEMENTATION
# =============================================================================


def write_artist_tags(
    audio,  # MediaFile instance
    artists: list[str],
    album_artists: list[str],
    config: TaggingConfig,
) -> dict[str, str | list[str]]:
    """Write artist tags to audio file with configurable strategy.

    This function implements the core tagging logic:
    1. Always writes ARTIST/ALBUMARTIST with delimiter-joined string
    2. Optionally writes ARTISTS/ALBUMARTISTS as multi-value tags

    The mediafile library provides two related but distinct attributes:

    audio.artist (singular):
        - Type: str
        - Writes a single string value
        - For MP3: Writes to TPE1 frame
        - For Opus: Writes single ARTIST field
        - For M4A: Writes to ©ART atom

    audio.artists (plural):
        - Type: list[str]
        - Writes multiple values (where format supports it)
        - For MP3: Writes to TXXX:ARTISTS frame (MusicBrainz convention)
        - For Opus: Writes multiple ARTIST fields
        - For M4A: Limited support (may only keep first value)

    Key insight: These are INDEPENDENT tags, not aliases.
    Writing to `artist` does NOT populate `artists` and vice versa.

    Args:
        audio: MediaFile instance to modify
        artists: List of track artists
        album_artists: List of album artists
        config: Tagging configuration

    Returns:
        Dict of what was written (for logging/debugging)
    """
    written = {}

    # Always write delimiter-joined ARTIST tag
    joined_artists = config.delimiter.join(artists)
    joined_album_artists = config.delimiter.join(album_artists)

    audio.artist = joined_artists
    audio.albumartist = joined_album_artists

    written["ARTIST"] = joined_artists
    written["ALBUMARTIST"] = joined_album_artists

    # Optionally write multi-value ARTISTS tag
    if config.write_artists_tag:
        audio.artists = artists
        audio.albumartists = album_artists

        written["ARTISTS"] = artists
        written["ALBUMARTISTS"] = album_artists

    return written


def tag_audio_file(
    path: Path,
    track: SampleTrack,
    config: TaggingConfig,
) -> dict[str, str | list[str]]:
    """Apply complete metadata to an audio file.

    Args:
        path: Path to audio file
        track: Track metadata
        config: Tagging configuration

    Returns:
        Dict of what was written
    """
    from mediafile import MediaFile

    audio = MediaFile(path)

    # Write basic metadata
    audio.title = track.title
    audio.album = track.album
    audio.year = track.year
    audio.track = track.track_number
    audio.tracktotal = track.total_tracks

    # Write artist tags with configurable strategy
    written = write_artist_tags(
        audio,
        artists=track.artists,
        album_artists=track.album_artists,
        config=config,
    )

    audio.save()
    return written


# =============================================================================
# TEST UTILITIES
# =============================================================================


def create_silent_audio_file(path: Path, format: str = "mp3") -> None:
    """Create a minimal silent audio file for testing using ffmpeg."""
    format_args = {
        "mp3": ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "0.1", "-q:a", "9"],
        "m4a": ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "0.1", "-c:a", "aac"],
        "opus": ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.1", "-c:a", "libopus"],
    }
    args = format_args.get(format, format_args["mp3"])
    cmd = ["ffmpeg", "-y", *args, str(path)]
    subprocess.run(cmd, capture_output=True, check=True)


def read_tags(path: Path) -> dict:
    """Read back all relevant tags from a file."""
    from mediafile import MediaFile

    audio = MediaFile(path)
    return {
        "title": audio.title,
        "artist": audio.artist,
        "artists": audio.artists,
        "albumartist": audio.albumartist,
        "albumartists": audio.albumartists,
        "album": audio.album,
        "year": audio.year,
        "track": audio.track,
    }


# =============================================================================
# DEMONSTRATIONS
# =============================================================================


def print_header(title: str, char: str = "=") -> None:
    """Print a formatted section header."""
    print(f"\n{char * 70}")
    print(title)
    print(char * 70)


def demonstrate_mediafile_api() -> None:
    """Explain the key mediafile API difference between artist and artists."""
    print_header("MEDIAFILE API: artist vs artists")
    print("""
    The mediafile library provides two related but distinct attributes:

    audio.artist (singular)
    -----------------------
    - Type: str
    - Writes a single string value
    - For MP3: Writes to TPE1 frame as single value
    - For Opus: Writes single ARTIST field
    - For M4A: Writes to ©ART atom

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


def demonstrate_server_presets() -> None:
    """Show tagging with different server configuration presets."""
    print_header("SERVER CONFIGURATION PRESETS")

    track = SAMPLE_TRACKS[1]  # Collaboration track

    for server in TargetServer:
        config = TaggingConfig.for_server(server)

        print(f"\n{'─' * 70}")
        print(f"TARGET: {server.value.upper()}")
        print(f"{'─' * 70}")
        print(f"  Delimiter: {repr(config.delimiter)}")
        print(f"  Write ARTISTS tag: {config.write_artists_tag}")
        print()
        print(f"  Track: {track.title}")
        print(f"  Artists: {track.artists}")
        print()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.mp3"
            create_silent_audio_file(path)

            written = tag_audio_file(path, track, config)
            tags = read_tags(path)

            print("  Tags written:")
            for tag, value in written.items():
                print(f"    {tag}: {repr(value)}")

            print()
            print("  Tags read back:")
            print(f"    artist: {repr(tags['artist'])}")
            print(f"    artists: {repr(tags['artists'])}")


def demonstrate_format_comparison() -> None:
    """Compare tagging across different audio formats."""
    print_header("FORMAT COMPARISON")

    config = TaggingConfig.for_server(TargetServer.NAVIDROME_JELLYFIN)
    track = SAMPLE_TRACKS[1]
    formats = ["mp3", "m4a", "opus"]
    results = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        for fmt in formats:
            path = Path(tmpdir) / f"test.{fmt}"
            try:
                create_silent_audio_file(path, format=fmt)
                tag_audio_file(path, track, config)
                tags = read_tags(path)
                results[fmt] = {
                    "artist": tags["artist"],
                    "artists": tags["artists"],
                    "success": True,
                }
            except Exception as e:
                results[fmt] = {"error": str(e), "success": False}

    print(f"\n  Track: {track.title}")
    print(f"  Artists: {track.artists}")
    print(f"  Config: delimiter={repr(config.delimiter)}, ARTISTS tag=True")
    print()

    print("  ┌─────────┬────────────────────────────────┬─────────────────────────────────────┐")
    print("  │ Format  │ ARTIST (singular)              │ ARTISTS (multi-value)               │")
    print("  ├─────────┼────────────────────────────────┼─────────────────────────────────────┤")

    for fmt in formats:
        r = results[fmt]
        if r["success"]:
            artist = r["artist"] or "(empty)"
            artists = r["artists"] if r["artists"] else "(not supported)"
            artist_disp = artist[:28] + ".." if len(str(artist)) > 30 else artist
            artists_disp = str(artists)[:33] + ".." if len(str(artists)) > 35 else str(artists)
            print(f"  │ {fmt.upper():<7} │ {artist_disp:<30} │ {artists_disp:<35} │")
        else:
            print(f"  │ {fmt.upper():<7} │ ERROR: {r['error'][:50]:<58} │")

    print("  └─────────┴────────────────────────────────┴─────────────────────────────────────┘")

    print("\n  Analysis:")
    for fmt in formats:
        r = results[fmt]
        if r["success"]:
            has_multi = r["artists"] is not None and len(r["artists"]) > 0
            status = "✓ written/read" if has_multi else "✗ not supported"
            print(f"    {fmt.upper()}: ARTISTS tag {status}")


def demonstrate_full_matrix() -> None:
    """Full compatibility matrix: all servers x all formats."""
    print_header("FULL COMPATIBILITY MATRIX")

    track = SAMPLE_TRACKS[1]
    formats = ["mp3", "m4a", "opus"]

    print(f"\n  Track: {track.title}")
    print(f"  Artists: {track.artists}")
    print()

    print("  ┌───────────────────┬─────────┬────────────────────────────────┬───────────────────┐")
    print("  │ Target            │ Format  │ ARTIST value                   │ ARTISTS written   │")
    print("  ├───────────────────┼─────────┼────────────────────────────────┼───────────────────┤")

    for server in TargetServer:
        config = TaggingConfig.for_server(server)

        for i, fmt in enumerate(formats):
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / f"test.{fmt}"
                try:
                    create_silent_audio_file(path, format=fmt)
                    tag_audio_file(path, track, config)
                    tags = read_tags(path)

                    artist = tags["artist"] or "(empty)"
                    artist_disp = artist[:28] + ".." if len(artist) > 30 else artist
                    has_artists = tags["artists"] is not None and len(tags["artists"]) > 0
                    artists_status = "✓ Yes" if has_artists else "✗ No"

                    server_name = server.value.upper() if i == 0 else ""
                    print(f"  │ {server_name:<17} │ {fmt.upper():<7} │ {artist_disp:<30} │ {artists_status:<17} │")

                except Exception as e:
                    server_name = server.value.upper() if i == 0 else ""
                    err = str(e)[:22]
                    print(f"  │ {server_name:<17} │ {fmt.upper():<7} │ ERROR: {err:<22}     │ {'N/A':<17} │")

        if server != list(TargetServer)[-1]:
            print("  ├───────────────────┼─────────┼────────────────────────────────┼───────────────────┤")

    print("  └───────────────────┴─────────┴────────────────────────────────┴───────────────────┘")


def demonstrate_server_compatibility() -> None:
    """Document which strategies work with which servers."""
    print_header("SERVER COMPATIBILITY REFERENCE")

    print("""
    DELIMITER RECOGNITION
    ┌───────────────┬──────┬───────────┬──────────┐
    │   Delimiter   │ Plex │ Navidrome │ Jellyfin │
    ├───────────────┼──────┼───────────┼──────────┤
    │ , (comma)     │  Y   │     Y     │    N     │
    │ ; (semicolon) │  N   │     Y     │    Y     │
    │ / (slash)     │  N   │     Y     │    Y     │
    │ | (pipe)      │  N   │     N     │    Y     │
    │ feat. / ft.   │  N   │     Y     │    N     │
    └───────────────┴──────┴───────────┴──────────┘

    STRATEGY SUPPORT BY SERVER
    ┌─────────────────────┬──────┬───────────┬──────────┐
    │ Strategy            │ Plex │ Navidrome │ Jellyfin │
    ├─────────────────────┼──────┼───────────┼──────────┤
    │ Delimiter ","       │  Y   │     Y     │    N     │
    │ Delimiter "/"       │  N   │     Y     │    Y     │
    │ Multi-value ARTIST  │ MP3  │     Y     │    Y     │
    │ Multi-value ARTISTS │  N   │     Y     │ (config) │
    │ Dual-tag (,)        │  Y   │     Y     │ (config) │
    └─────────────────────┴──────┴───────────┴──────────┘

    FORMAT-SPECIFIC: OPUS
    ┌─────────────────────┬──────┬───────────┬──────────┐
    │ Strategy            │ Plex │ Navidrome │ Jellyfin │
    ├─────────────────────┼──────┼───────────┼──────────┤
    │ Any tagging method  │  X   │     Y     │    Y     │
    └─────────────────────┴──────┴───────────┴──────────┘
    X = Plex has metadata reading issues with Opus (broken since 2016)

    FORMAT-SPECIFIC: MP3 (ID3v2.4)
    ┌─────────────────────┬──────┬───────────┬──────────┐
    │ Strategy            │ Plex │ Navidrome │ Jellyfin │
    ├─────────────────────┼──────┼───────────┼──────────┤
    │ Delimiter ","       │  Y   │     Y     │    N     │
    │ Delimiter "/"       │  N   │     Y     │    Y     │
    │ Multi-value ARTIST  │  Y   │     Y     │    Y     │
    │ Multi-value ARTISTS │  N   │     Y     │ (config) │
    └─────────────────────┴──────┴───────────┴──────────┘
    * MP3 has the best cross-server multi-value support

    FORMAT-SPECIFIC: M4A
    ┌─────────────────────┬──────┬───────────┬──────────┐
    │ Strategy            │ Plex │ Navidrome │ Jellyfin │
    ├─────────────────────┼──────┼───────────┼──────────┤
    │ Delimiter ","       │  Y   │     Y     │    N     │
    │ Delimiter "/"       │  N   │     Y     │    Y     │
    │ Multi-value ARTIST  │  -   │     -     │    -     │
    │ Multi-value ARTISTS │  -   │     -     │    -     │
    └─────────────────────┴──────┴───────────┴──────────┘
    - = Not supported by format (M4A lacks multi-value artist support)

    LEGEND
    ------
    Y = Works out of the box
    N = Not supported/parsed
    X = Format broken on server
    - = Not supported by audio format
    (config) = Requires server setting (PreferNonstandardArtistsTag)
    """)


def demonstrate_recommendations() -> None:
    """Show recommended strategy by target server combination."""
    print_header("RECOMMENDED STRATEGY BY TARGET")

    print("""
    ┌─────────────────────────┬────────┬───────────┬───────────┐
    │ Target Server(s)        │  Opus  │    MP3    │    M4A    │
    ├─────────────────────────┼────────┼───────────┼───────────┤
    │ Plex only               │ AVOID  │ delim "," │ delim "," │
    │ Jellyfin only           │ delim  │ delim "/" │ delim "/" │
    │ Navidrome only          │ ARTISTS│ ARTISTS   │ delim "/" │
    │ Jellyfin + Navidrome    │ delim  │ delim+ART │ delim "/" │
    │ Plex + Navidrome        │ AVOID  │ dual ","  │ delim "," │
    │ Plex + Jellyfin         │ AVOID  │ dual ","* │ delim ","*│
    │ All three               │ AVOID  │ dual ","* │ delim ","*│
    └─────────────────────────┴────────┴───────────┴───────────┘

    Key:
    - AVOID    = Don't use this format for this target
    - delim X  = Use delimiter X in ARTIST tag only
    - ARTISTS  = Use multi-value ARTISTS tag (Navidrome preferred)
    - delim+ART= Use delimiter in ARTIST + write ARTISTS tag
    - dual X   = Use delimiter X + write ARTISTS tag
    - *        = Jellyfin needs PreferNonstandardArtistsTag for ARTISTS
    """)


def demonstrate_edge_cases() -> None:
    """Document edge cases to consider."""
    print_header("EDGE CASES TO CONSIDER")

    print("""
    1. BAND NAMES WITH DELIMITERS (e.g., AC/DC)
       - Slash delimiter would incorrectly split "AC/DC" into "AC" and "DC"
       - Jellyfin has built-in whitelist for known bands
       - Solution: Use multi-value ARTISTS tag (not delimiter parsing)
       - Alternative: Implement user-configurable whitelist

    2. NO COMMON DELIMITER FOR ALL SERVERS
       - Comma (,): Works in Plex + Navidrome, NOT Jellyfin
       - Slash (/): Works in Navidrome + Jellyfin, NOT Plex
       - Solution: Dual-tag mode (delimiter ARTIST + multi-value ARTISTS)

    3. FORMAT LIMITATIONS
       - Opus: Full multi-value support, but Plex can't read metadata
       - MP3: Best cross-server support, use ID3v2.4
       - M4A: No multi-value support, delimiter-only
    """)


def demonstrate_implementation() -> None:
    """Show recommended implementation for yubal."""
    print_header("RECOMMENDED IMPLEMENTATION FOR YUBAL")

    print('''
    def write_artist_tags(
        audio: MediaFile,
        artists: list[str],
        album_artists: list[str],
        delimiter: str = " / ",
        write_artists_tag: bool = False,
    ) -> None:
        """
        Write artist tags with configurable strategy.

        Args:
            audio: MediaFile instance
            artists: List of track artists
            album_artists: List of album artists
            delimiter: Delimiter for joining artists (default: " / ")
            write_artists_tag: If True, write multi-value ARTISTS tag
        """
        # Always write delimiter-joined tags
        audio.artist = delimiter.join(artists)
        audio.albumartist = delimiter.join(album_artists)

        # Optionally write multi-value tags for Navidrome/Jellyfin
        if write_artists_tag:
            audio.artists = artists
            audio.albumartists = album_artists


    # Configuration presets:
    PRESETS = {
        "plex":              {"delimiter": ", ",  "write_artists_tag": False},
        "jellyfin":          {"delimiter": " / ", "write_artists_tag": False},
        "navidrome":         {"delimiter": " / ", "write_artists_tag": True},
        "navidrome+jellyfin":{"delimiter": " / ", "write_artists_tag": True},
        "all":               {"delimiter": ", ",  "write_artists_tag": True},
    }
    ''')


# =============================================================================
# MAIN
# =============================================================================


def main() -> None:
    """Run all demonstrations."""
    print("=" * 70)
    print("MULTI-ARTIST TAGGING PROOF OF CONCEPT")
    print("=" * 70)

    # 1. Explain the API
    demonstrate_mediafile_api()

    # 2. Show server presets with real file tagging
    demonstrate_server_presets()

    # 3. Compare formats
    demonstrate_format_comparison()

    # 4. Full matrix: servers x formats
    demonstrate_full_matrix()

    # 5. Reference documentation
    demonstrate_server_compatibility()
    demonstrate_recommendations()
    demonstrate_edge_cases()

    # 6. Implementation example
    demonstrate_implementation()

    print_header("END OF PROOF OF CONCEPT")
    print("\nSee docs/servers/multi-artist-tagging.md for complete analysis")


if __name__ == "__main__":
    try:
        from mediafile import MediaFile  # noqa: F401

        main()

    except ImportError:
        print("ERROR: mediafile package not installed")
        print("Install with: pip install mediafile")
        exit(1)
