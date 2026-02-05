#!/usr/bin/env python3
"""Debug script to inspect raw ytmusicapi album response."""

import json
import re
import sys

from ytmusicapi import YTMusic


def parse_album_id(url: str) -> str:
    """Extract album ID from URL or return as-is."""
    # Handle music.youtube.com/browse/MPREb_... or /playlist?list=OLAK5uy_...
    match = re.search(r"browse/([^?&]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"list=([^&]+)", url)
    if match:
        return match.group(1)
    # Assume it's already an ID
    return url


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python get_album.py <album_url_or_id>")
        sys.exit(1)

    album_id = parse_album_id(sys.argv[1])
    print(f"Fetching album: {album_id}\n", file=sys.stderr)

    ytm = YTMusic()
    data = ytm.get_album(album_id)

    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    main()
