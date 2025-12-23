# ytad - YouTube Album Downloader

Download albums from YouTube Music and auto-tag with beets.

## Requirements

- Python 3.12+
- ffmpeg

## Installation

### From Source (Development)

```bash
git clone https://github.com/youruser/ytad.git
cd ytad
uv sync
```

### From Wheel (Production)

```bash
# Build on source machine
uv build

# Install on target machine
pip install ytad-0.1.0-py3-none-any.whl
```

### From Git URL

```bash
pip install git+https://github.com/youruser/ytad.git
```

## Prerequisites

Install ffmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

## Usage

### Download and tag an album

```bash
ytad sync "https://music.youtube.com/playlist?list=..."
```

### Tag existing files

```bash
ytad tag /path/to/downloaded/album
```

### Check library health

```bash
ytad doctor
```

### View file metadata

```bash
ytad info /path/to/file.mp3
```

## Commands

| Command    | Description                      |
|------------|----------------------------------|
| `sync`     | Download and tag in one step     |
| `download` | Download only (no tagging)       |
| `tag`      | Tag and organize existing files  |
| `doctor`   | Check/repair library database    |
| `info`     | Display file metadata            |
| `nuke`     | Remove all data and start fresh  |

## Configuration

Edit `config/beets_config.yaml` to customize:

- `paths.default` - file organization pattern
- `match.strong_rec_thresh` - auto-match confidence
- `fetchart.sources` - album art sources

## License

MIT
