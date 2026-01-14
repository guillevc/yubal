#!/usr/bin/env python3
"""Debug script to inspect raw ytmusicapi playlist response."""

import json
import re
import sys

from ytmusicapi import YTMusic


def parse_playlist_id(url: str) -> str:
    """Extract playlist ID from URL or return as-is."""
    match = re.search(r"list=([^&]+)", url)
    return match.group(1) if match else url


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python debug_playlist.py <playlist_url_or_id>")
        sys.exit(1)

    playlist_id = parse_playlist_id(sys.argv[1])
    print(f"Fetching playlist: {playlist_id}\n", file=sys.stderr)

    ytm = YTMusic()
    data = ytm.get_playlist(playlist_id, limit=None)

    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    main()
