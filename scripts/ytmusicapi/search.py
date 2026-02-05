#!/usr/bin/env python3
"""Debug script to inspect raw ytmusicapi search response."""

import json
import sys

from ytmusicapi import YTMusic


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python search.py <query> [filter]")
        print(
            "Filters: songs, videos, albums, artists, playlists, "
            "community_playlists, featured_playlists, uploads"
        )
        sys.exit(1)

    query = sys.argv[1]
    filter_type = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Searching: {query}", file=sys.stderr)
    if filter_type:
        print(f"Filter: {filter_type}", file=sys.stderr)
    print(file=sys.stderr)

    ytm = YTMusic()
    data = ytm.search(query, filter=filter_type)

    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    main()
