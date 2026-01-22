> [!TIP]
> **New in v0.2.0:** Playlist support is here! Download entire playlists with a single URL.

> [!IMPORTANT]
> **Upgrading from v0.1?** The folder structure and config have changed. See the [v0.2.0 release notes](https://github.com/guillevc/yubal/releases/tag/v0.2.0) for migration steps.

<div align="center">

# yubal

**YouTube Music album & playlist downloader with automatic metadata tagging.**

[![CI](https://github.com/guillevc/yubal/actions/workflows/ci.yaml/badge.svg)](https://github.com/guillevc/yubal/actions/workflows/ci.yaml)
[![Release](https://img.shields.io/github/v/release/guillevc/yubal)](https://github.com/guillevc/yubal/releases)
[![Docker](https://img.shields.io/badge/ghcr.io-blue?logo=docker&logoColor=white)](https://ghcr.io/guillevc/yubal)
[![codecov](https://codecov.io/gh/guillevc/yubal/branch/master/graph/badge.svg)](https://codecov.io/gh/guillevc/yubal)

<picture>
  <img src="docs/demo.gif" alt="yubal demo">
</picture>

<sub>GIF is 3× speed</sub>

</div>

## 📖 Overview

**yubal** is a self-hosted app for building a local music library. Paste a YouTube Music album or playlist URL, and yubal handles downloading, tagging, and album art—automatically.

```
data/
├── Pink Floyd/
│   └── 1973 - The Dark Side of the Moon/
│       ├── 01 - Speak to Me.opus
│       ├── 02 - Breathe.opus
│       └── cover.jpg
│
├── Radiohead/
│   └── 1997 - OK Computer/
│       ├── 01 - Airbag.opus
│       ├── 02 - Paranoid Android.opus
│       └── cover.jpg
│
└── Playlists/
    ├── My Favorites.m3u
    └── My Favorites.jpg
```

Albums are organized by artist and year. When downloading a playlist, each track goes to its respective album folder—the M3U file just references them, no duplicates:

```m3u
#EXTM3U
#EXTINF:239,Pink Floyd - Breathe
../Pink Floyd/1973 - The Dark Side of the Moon/02 - Breathe.opus
#EXTINF:386,Radiohead - Paranoid Android
../Radiohead/1997 - OK Computer/02 - Paranoid Android.opus
```

## ✨ Features

- **Web UI** — Real-time progress, job queue, responsive design
- **Smart tagging** — Metadata from YouTube Music with fuzzy track matching
- **Albums & playlists** — Automatic album detection, M3U playlist generation
- **Smart deduplication** — Tracks indexed by path, never downloaded twice across playlists or albums
- **Format options** — Native `opus` (best quality), or transcode to `mp3`/`m4a`
- **Media server ready** — Tested with [Navidrome, Jellyfin and Gonic](#-media-servers-integration)

## 🚀 Quick Start

```yaml
# compose.yaml
services:
  yubal:
    image: ghcr.io/guillevc/yubal:latest
    ports:
      - 8000:8000
    environment:
      YUBAL_TZ: UTC
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    restart: unless-stopped
```

```bash
docker compose up -d
# Open http://localhost:8000
```

## ⚙️ Configuration

| Variable              | Description                          | Default (Docker) |
| --------------------- | ------------------------------------ | ---------------- |
| `YUBAL_DATA`          | Music library output                 | `/app/data`      |
| `YUBAL_CONFIG`        | Config directory                     | `/app/config`    |
| `YUBAL_AUDIO_FORMAT`  | `opus`, `mp3`, or `m4a`              | `opus`           |
| `YUBAL_AUDIO_QUALITY` | Transcode quality (0=best, 10=worst) | `0`              |
| `YUBAL_TZ`            | Timezone (IANA format)               | `UTC`            |
| `YUBAL_LOG_LEVEL`     | `DEBUG`, `INFO`, `WARNING`, `ERROR`  | `INFO`           |

<details>
<summary>All options</summary>
| Variable             | Description            | Default (Docker) |
| -------------------- | ---------------------- | ---------------- |
| `YUBAL_HOST`         | Server bind address    | `0.0.0.0`        |
| `YUBAL_PORT`         | Server port            | `8000`           |
| `YUBAL_DEBUG`        | Debug mode             | `false`          |
| `YUBAL_CORS_ORIGINS` | Allowed CORS origins   | `["*"]`          |
| `YUBAL_RELOAD`       | Auto-reload (dev only) | `false`          |
| `YUBAL_TEMP`         | Temp directory         | System temp      |
</details>

## 🔌 Media Servers Integration

yubal organizes downloads as `Artist/Year - Album/NN - Track.ext` and writes both slash-separated `ARTIST` and multi-value `ARTISTS` tags across all audio formats.

Configure your server to read `ARTISTS` tags for proper multi-artist linking.

| Feature           | Navidrome | Jellyfin | Gonic |
| ----------------- | :-------: | :------: | :---: |
| Folder structure  |    ✅     |    ✅    |  ✅   |
| Multi-artist tags |    ✅     |    ⚙️    |  ⚙️   |
| M3U playlists     |    ✅     |    ✅    |  ❌   |

✅ Works out of the box · ⚙️ Requires configuration

<details>
<summary><b>Navidrome</b> (works out of the box)</summary>

No configuration required. Optionally, make imported playlists public:

```bash
ND_DEFAULTPLAYLISTPUBLICVISIBILITY=true
```

See [Navidrome docs](https://www.navidrome.org/docs/usage/configuration/options/).

</details>

<details>
<summary><b>Jellyfin</b></summary>

For multi-artist support, enable the non-standard artists tag:

1. **Dashboard → Libraries → Music Library → Manage Library**
2. Check **Use non-standard artists tags**
3. Save and rescan

</details>

<details>
<summary><b>Gonic</b></summary>

For multi-artist support:

```bash
GONIC_MULTI_VALUE_ARTIST=multi
GONIC_MULTI_VALUE_ALBUM_ARTIST=multi
```

M3U playlists with relative paths are not supported ([pending PR in gonic](https://github.com/sentriz/gonic/pull/537)).

</details>

## 🍪 Cookies (Optional)

For age-restricted content, private playlists, or higher bitrate (Premium):

1. Export cookies with a browser extension ([yt-dlp guide](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp))
2. Place at `config/ytdlp/cookies.txt` or upload via the web UI

> [!CAUTION]
> Cookie usage may trigger stricter rate limiting and could put your account at risk. See [#3](https://github.com/guillevc/yubal/issues/3) and [yt-dlp wiki](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#youtube).

## 🗺️ Roadmap

- [x] Cookies upload via Web UI
- [x] Multi-arch Docker (amd64/arm64)
- [x] Configurable audio format
- [x] Playlist support with M3U generation
- [ ] Flat folder structure mode (Do not organize into subfolders)
- [ ] Browser extension
- [ ] Batch import (multiple URLs)
- [ ] Post-import webhooks (Navidrome/Jellyfin/Gonic)

## 💜 Support

If yubal is useful to you, consider supporting its development:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/guillevc)

[![Sponsor](https://img.shields.io/badge/sponsor-GitHub-ea4aaa?logo=github)](https://github.com/sponsors/guillevc)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=guillevc/yubal&type=Date)](https://star-history.com/#guillevc/yubal&Date)

## 🤝 Acknowledgments

Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [ytmusicapi](https://github.com/sigma67/ytmusicapi).

Thanks to everyone who's starred, shared, or contributed.

## License

[MIT](LICENSE)

---

<sub>For personal archiving only. Comply with YouTube's Terms of Service and applicable copyright laws.</sub>
