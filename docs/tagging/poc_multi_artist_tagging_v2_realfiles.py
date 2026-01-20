#!/usr/bin/env python3
"""
Multi-Artist Tagging Proof of Concept
======================================

This PoC demonstrates how to implement configurable multi-artist tagging
with the mediafile library for maximum compatibility across media servers:
- Plex (comma delimiter only)
- Navidrome (prefers ARTISTS tag, supports multiple delimiters)
- Jellyfin (supports multiple delimiters, ARTISTS requires setting)

Run this script to create sample tagged files and inspect them.

Requirements:
    pip install mediafile

Usage:
    python multi_artist_tagging_poc.py
"""

from __future__ import annotations

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
        use_dual_tag_mode: If True, writes both ARTIST (delimited) and ARTISTS (multi-value).
        write_artists_tag: If True, writes the non-standard ARTISTS tag.

    Server Compatibility:
        - Plex: Only reads comma-delimited ARTIST, ignores ARTISTS
        - Navidrome: Prefers ARTISTS, falls back to delimiter parsing
        - Jellyfin: Reads ARTIST with delimiters, ARTISTS requires setting
    """

    delimiter: str = " / "
    use_dual_tag_mode: bool = False
    write_artists_tag: bool = False

    @classmethod
    def for_server(cls, server: TargetServer) -> TaggingConfig:
        """Get recommended config for target server(s).

        Delimiter choices:
        - Comma (,): Only works in Plex and Navidrome, NOT Jellyfin
        - Slash (/): Works in Navidrome and Jellyfin, NOT Plex
        - Semicolon (;): Works in Navidrome and Jellyfin, NOT Plex

        Dual-tag mode:
        - Writes ARTIST with delimiter (for Plex compatibility)
        - Writes ARTISTS as multi-value (for Navidrome/Jellyfin)
        """
        configs = {
            # Plex only: comma is the only recognized delimiter
            TargetServer.PLEX: cls(
                delimiter=", ",
                use_dual_tag_mode=False,
                write_artists_tag=False,
            ),
            # Navidrome only: prefers ARTISTS tag
            TargetServer.NAVIDROME: cls(
                delimiter=" / ",
                use_dual_tag_mode=False,
                write_artists_tag=True,  # Navidrome prefers this
            ),
            # Jellyfin only: slash delimiter works out of the box
            TargetServer.JELLYFIN: cls(
                delimiter=" / ",
                use_dual_tag_mode=False,
                write_artists_tag=False,
            ),
            # Navidrome + Jellyfin: slash works in both
            TargetServer.NAVIDROME_JELLYFIN: cls(
                delimiter=" / ",
                use_dual_tag_mode=False,
                write_artists_tag=True,  # Benefits Navidrome
            ),
            # All servers: dual-tag mode for maximum compatibility
            # Comma in ARTIST for Plex, ARTISTS tag for Navidrome/Jellyfin
            TargetServer.ALL: cls(
                delimiter=", ",  # Comma for Plex
                use_dual_tag_mode=True,  # Write both tags
                write_artists_tag=True,
            ),
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


# Sample tracks with various artist configurations
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
        title="Multiple Artists Track",
        artists=["Major Lazer", "DJ Snake", "MO"],
        album="Peace Is The Mission",
        album_artists=["Major Lazer"],
        track_number=3,
    ),
    SampleTrack(
        title="Problematic Band Name",
        artists=["AC/DC"],  # Contains slash - should NOT be split!
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
    if config.write_artists_tag or config.use_dual_tag_mode:
        # mediafile supports setting 'artists' (plural) as a list
        # This writes the non-standard ARTISTS tag
        audio.artists = artists
        audio.albumartists = album_artists

        written["ARTISTS"] = artists
        written["ALBUMARTISTS"] = album_artists

    return written


def tag_sample_file(
    path: Path,
    track: SampleTrack,
    config: TaggingConfig,
) -> dict[str, str | list[str]]:
    """Apply complete metadata to a sample audio file.

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
# DEMONSTRATION / INSPECTION
# =============================================================================


def create_silent_audio_file(path: Path, format: str = "mp3") -> None:
    """Create a minimal silent audio file for testing using ffmpeg.

    In a real scenario, you'd have actual audio files.
    This creates a valid 1-second silent file that mediafile can tag.
    """
    import subprocess

    format_args = {
        "mp3": ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "0.1", "-q:a", "9"],
        "m4a": ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "0.1", "-c:a", "aac"],
        "opus": ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.1", "-c:a", "libopus"],
    }

    args = format_args.get(format, format_args["mp3"])
    cmd = ["ffmpeg", "-y", *args, str(path)]

    subprocess.run(cmd, capture_output=True, check=True)


def inspect_tags(path: Path) -> dict:
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


def demonstrate_tagging():
    """Demonstrate tagging with different server configurations."""
    print("=" * 70)
    print("MULTI-ARTIST TAGGING PROOF OF CONCEPT")
    print("=" * 70)

    # Test each server configuration
    for server in TargetServer:
        config = TaggingConfig.for_server(server)

        print(f"\n{'─' * 70}")
        print(f"TARGET: {server.value.upper()}")
        print(f"{'─' * 70}")
        print(f"  Delimiter: {repr(config.delimiter)}")
        print(f"  Dual-tag mode: {config.use_dual_tag_mode}")
        print(f"  Write ARTISTS tag: {config.write_artists_tag}")
        print()

        # Tag a sample track
        track = SAMPLE_TRACKS[1]  # Collaboration track with 2 artists

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.mp3"
            create_silent_audio_file(path)

            written = tag_sample_file(path, track, config)

            print(f"  Track: {track.title}")
            print(f"  Artists: {track.artists}")
            print()
            print("  Tags written:")
            for tag, value in written.items():
                print(f"    {tag}: {repr(value)}")

            # Read back and verify
            print()
            print("  Tags read back:")
            tags = inspect_tags(path)
            print(f"    artist: {repr(tags['artist'])}")
            print(f"    artists: {repr(tags['artists'])}")


def demonstrate_formats():
    """Demonstrate tagging across different audio formats."""
    print(f"\n{'=' * 70}")
    print("FORMAT COMPARISON (Navidrome+Jellyfin config)")
    print("=" * 70)

    config = TaggingConfig.for_server(TargetServer.NAVIDROME_JELLYFIN)
    track = SAMPLE_TRACKS[1]  # Collaboration track

    formats = ["mp3", "m4a", "opus"]
    results = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        for fmt in formats:
            path = Path(tmpdir) / f"test.{fmt}"
            try:
                create_silent_audio_file(path, format=fmt)
                tag_sample_file(path, track, config)
                tags = inspect_tags(path)
                results[fmt] = {
                    "artist": tags["artist"],
                    "artists": tags["artists"],
                    "success": True,
                }
            except Exception as e:
                results[fmt] = {"error": str(e), "success": False}

    # Print results table
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
            # Truncate for display
            artist_display = artist[:28] + ".." if len(str(artist)) > 30 else artist
            artists_display = str(artists)[:33] + ".." if len(str(artists)) > 35 else str(artists)
            print(f"  │ {fmt.upper():<7} │ {artist_display:<30} │ {artists_display:<35} │")
        else:
            print(f"  │ {fmt.upper():<7} │ ERROR: {r['error'][:50]:<58} │")

    print("  └─────────┴────────────────────────────────┴─────────────────────────────────────┘")

    # Analysis
    print("\n  Analysis:")
    for fmt in formats:
        r = results[fmt]
        if r["success"]:
            has_multi = r["artists"] is not None and len(r["artists"]) > 0
            print(f"    {fmt.upper()}: ARTISTS tag {'✓ supported' if has_multi else '✗ not written/read'}")


def demonstrate_all_combinations():
    """Full matrix: all servers x all formats."""
    print(f"\n{'=' * 70}")
    print("FULL COMPATIBILITY MATRIX")
    print("=" * 70)

    track = SAMPLE_TRACKS[1]
    formats = ["mp3", "m4a", "opus"]

    print(f"\n  Track: {track.title}")
    print(f"  Artists: {track.artists}")
    print()

    # Header
    print("  ┌───────────────────┬─────────┬────────────────────────────────┬───────────────────┐")
    print("  │ Target            │ Format  │ ARTIST value                   │ ARTISTS supported │")
    print("  ├───────────────────┼─────────┼────────────────────────────────┼───────────────────┤")

    for server in TargetServer:
        config = TaggingConfig.for_server(server)

        for i, fmt in enumerate(formats):
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / f"test.{fmt}"
                try:
                    create_silent_audio_file(path, format=fmt)
                    tag_sample_file(path, track, config)
                    tags = inspect_tags(path)

                    artist = tags["artist"] or "(empty)"
                    artist_display = artist[:28] + ".." if len(artist) > 30 else artist
                    has_artists = tags["artists"] is not None and len(tags["artists"]) > 0
                    artists_status = "✓ Yes" if has_artists else "✗ No"

                    # Show server name only on first format
                    server_name = server.value.upper() if i == 0 else ""
                    print(f"  │ {server_name:<17} │ {fmt.upper():<7} │ {artist_display:<30} │ {artists_status:<17} │")

                except Exception as e:
                    server_name = server.value.upper() if i == 0 else ""
                    print(f"  │ {server_name:<17} │ {fmt.upper():<7} │ ERROR: {str(e)[:22]:<30} │ {'N/A':<17} │")

        # Separator between servers
        if server != list(TargetServer)[-1]:
            print("  ├───────────────────┼─────────┼────────────────────────────────┼───────────────────┤")

    print("  └───────────────────┴─────────┴────────────────────────────────┴───────────────────┘")

    # Show problematic cases
    print(f"\n{'=' * 70}")
    print("EDGE CASES TO CONSIDER")
    print("=" * 70)

    print("\n1. Band names with delimiters (AC/DC):")
    print("   - Slash delimiter would incorrectly split 'AC/DC' into 'AC' and 'DC'")
    print("   - Jellyfin has built-in whitelist for known bands")
    print("   - Consider implementing a user-configurable whitelist")

    print("\n2. No common delimiter for all servers:")
    print("   - Comma works in Plex + Navidrome, NOT Jellyfin")
    print("   - Slash works in Navidrome + Jellyfin, NOT Plex")
    print("   - Solution: Dual-tag mode (ARTIST + ARTISTS)")

    print("\n3. Format limitations:")
    print("   - Opus: Full multi-value support")
    print("   - MP3: Multi-value only in ID3v2.4")
    print("   - M4A: No multi-value support, delimiter only")


def demonstrate_format_differences():
    """Show how tags work differently across formats."""
    print(f"\n{'=' * 70}")
    print("FORMAT-SPECIFIC BEHAVIOR")
    print("=" * 70)

    formats_info = """
    Opus (Vorbis Comments):
    ├── Multi-value ARTIST: Supported natively
    ├── ARTISTS tag: Supported
    └── Recommendation: Use multi-value ARTIST

    MP3 (ID3v2.3/v2.4):
    ├── Multi-value TPE1: Only ID3v2.4 with null separator
    ├── ARTISTS tag: TXXX custom frame
    └── Recommendation: Delimiter in ARTIST, TXXX for ARTISTS

    M4A (MP4/iTunes):
    ├── Multi-value ©ART: Not supported (uses last value)
    ├── ARTISTS tag: Custom atom (limited support)
    └── Recommendation: Delimiter only
    """
    print(formats_info)


if __name__ == "__main__":
    try:
        from mediafile import MediaFile  # noqa: F401

        demonstrate_tagging()
        demonstrate_formats()
        demonstrate_all_combinations()
        demonstrate_format_differences()

        print(f"\n{'=' * 70}")
        print("See docs/servers/multi-artist-tagging.md for complete analysis")
        print("=" * 70)

    except ImportError:
        print("ERROR: mediafile package not installed")
        print("Install with: pip install mediafile")
        exit(1)
