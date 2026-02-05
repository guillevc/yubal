#!/usr/bin/env python3
"""Debug script to inspect raw ytmusicapi get_watch_playlist response."""

import argparse
import json
import re
import sys

from ytmusicapi import YTMusic


def parse_video_id(url: str) -> str:
    """Extract video ID from URL or return as-is."""
    match = re.search(r"v=([^&]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"youtu\.be/([^?]+)", url)
    if match:
        return match.group(1)
    return url


def parse_playlist_id(url: str) -> str:
    """Extract playlist ID from URL or return as-is."""
    match = re.search(r"list=([^&]+)", url)
    if match:
        return match.group(1)
    match = re.search(r"browse/([^?&]+)", url)
    if match:
        return match.group(1)
    return url


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Get watch playlist from YouTube Music",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python get_watch_playlist.py -v dQw4w9WgXcQ
  python get_watch_playlist.py -p OLAK5uy_xxx --limit 50
  python get_watch_playlist.py -v dQw4w9WgXcQ --radio
  python get_watch_playlist.py -p OLAK5uy_xxx --shuffle
        """,
    )
    parser.add_argument(
        "-v",
        "--video-id",
        type=str,
        default=None,
        help="Video ID or URL of the played video",
    )
    parser.add_argument(
        "-p",
        "--playlist-id",
        type=str,
        default=None,
        help="Playlist ID or URL of the played playlist or album",
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        default=25,
        help="Minimum number of watch playlist items to return (default: 25)",
    )
    parser.add_argument(
        "-r",
        "--radio",
        action="store_true",
        help="Get a radio playlist (changes each time)",
    )
    parser.add_argument(
        "-s",
        "--shuffle",
        action="store_true",
        help="Shuffle the playlist (requires --playlist-id, no --radio)",
    )

    args = parser.parse_args()

    if not args.video_id and not args.playlist_id:
        parser.error("At least one of --video-id or --playlist-id is required")

    video_id = parse_video_id(args.video_id) if args.video_id else None
    playlist_id = parse_playlist_id(args.playlist_id) if args.playlist_id else None

    print(f"videoId: {video_id}", file=sys.stderr)
    print(f"playlistId: {playlist_id}", file=sys.stderr)
    print(f"limit: {args.limit}", file=sys.stderr)
    print(f"radio: {args.radio}", file=sys.stderr)
    print(f"shuffle: {args.shuffle}", file=sys.stderr)
    print(file=sys.stderr)

    ytm = YTMusic()
    data = ytm.get_watch_playlist(
        videoId=video_id,
        playlistId=playlist_id,
        limit=args.limit,
        radio=args.radio,
        shuffle=args.shuffle,
    )

    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    main()
