# yubal CLI

Command-line interface for extracting metadata and downloading tracks from YouTube Music.

> **Note:** The CLI is maintained but may lack some features available in the web UI, which is the main focus of the project.

## Installation

Install the CLI so `yubal` is available on your PATH:

```sh
uv tool install './packages/yubal[cli]'
```

To update after pulling new changes:

```sh
uv tool upgrade yubal
```

To uninstall:

```sh
uv tool uninstall yubal
```

For development, you can also run it via:

```sh
uv run yubal        # from the repo root
just cli             # shorthand
```

## Usage

```
yubal [OPTIONS] COMMAND [ARGS]
```

### Global options

| Option | Description |
| --- | --- |
| `-v`, `--verbose` | Enable debug logging |

### Commands

#### `meta` - Extract metadata

Extract structured metadata from a YouTube Music URL without downloading.

```sh
yubal meta "https://music.youtube.com/playlist?list=OLAK5uy_xxx"
yubal meta "https://music.youtube.com/watch?v=VIDEO_ID" --json
```

| Option | Description |
| --- | --- |
| `--json` | Output as JSON |
| `--cookies PATH` | Path to cookies.txt for authentication |

#### `download` - Download tracks

Download tracks from a YouTube Music URL (single track, album, or playlist).

```sh
yubal download "https://music.youtube.com/playlist?list=OLAK5uy_xxx" ~/Music
yubal download "https://music.youtube.com/watch?v=VIDEO_ID" ~/Music --codec flac
```

| Option | Description |
| --- | --- |
| `--codec` | Audio codec: `opus` (default), `flac`, `m4a`, `mp3` |
| `--quality` | Audio quality, 0 (best) to 10 (worst). Lossy codecs only |
| `--max-items` | Maximum number of tracks to download |
| `--cookies PATH` | Path to cookies.txt for authentication |
| `--no-m3u` | Disable M3U playlist file generation |
| `--no-cover` | Disable cover image saving |
| `--album-m3u` | Generate M3U files for albums (off by default) |
| `--no-replaygain` | Disable ReplayGain tagging |

#### `tags` - Inspect audio file tags

Display metadata tags from audio files, with ReplayGain/R128 highlighting.

```sh
yubal tags ~/Music/Artist/Album/track.opus
yubal tags ~/Music/Artist/Album/*.opus
yubal tags ~/Music/Artist/Album/ -r
```

| Option | Description |
| --- | --- |
| `--json` | Output as JSON |
| `-r`, `--replaygain-only` | Show only ReplayGain/R128 fields in table format |

#### `version` - Show version

```sh
yubal version
```
