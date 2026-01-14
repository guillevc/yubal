#!/usr/bin/env python3
"""Debug script to inspect raw ytmusicapi song response."""

import json
import re
import sys

from ytmusicapi import YTMusic


def parse_video_id(url: str) -> str:
    """Extract video ID from URL or return as-is."""
    # Handle youtube.com/watch?v=ID
    match = re.search(r"v=([^&]+)", url)
    if match:
        return match.group(1)
    # Handle youtu.be/ID
    match = re.search(r"youtu\.be/([^?]+)", url)
    if match:
        return match.group(1)
    # Assume it's already an ID
    return url


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python debug_song.py <video_url_or_id>")
        sys.exit(1)

    video_id = parse_video_id(sys.argv[1])
    print(f"Fetching song: {video_id}\n", file=sys.stderr)

    ytm = YTMusic()
    data = ytm.get_song(video_id)

    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    main()
