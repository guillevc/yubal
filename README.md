<div align="center">

# yubal

Self-hosted YouTube Music downloader. Paste a link, get a tagged, organized library.

Playlist sync. Artist/year sorting. Duplicate detection. Media server ready.

[![CI](https://github.com/guillevc/yubal/actions/workflows/ci.yaml/badge.svg)](https://github.com/guillevc/yubal/actions/workflows/ci.yaml)
[![Release](https://img.shields.io/github/v/release/guillevc/yubal)](https://github.com/guillevc/yubal/releases)
[![Firefox Add-on](https://img.shields.io/amo/v/yubal?label=firefox%20add-on&logo=firefox&logoColor=white&color=orange)](https://addons.mozilla.org/firefox/addon/yubal/)
[![Chrome Extension](https://img.shields.io/github/v/release/guillevc/yubal?filter=ext-v*&label=chrome%20extension&logo=googlechrome&logoColor=white&color=orange)](https://github.com/guillevc/yubal/releases?q=🧩)
[![Docker](https://img.shields.io/badge/ghcr.io-blue?logo=docker&logoColor=white)](https://ghcr.io/guillevc/yubal)
[![codecov](https://codecov.io/gh/guillevc/yubal/branch/master/graph/badge.svg)](https://codecov.io/gh/guillevc/yubal)

<picture>
  <img src="docs/demo.gif" alt="yubal demo" width="75%">
</picture>

</div>

<br/>

## 📖 How It Works

Downloading music is easy. _Organizing_ it is the hard part.

yubal takes a YouTube Music URL and produces a clean, tagged music library:

```
data/
├── Pink Floyd/
│   └── 1973 - The Dark Side of the Moon/
│       ├── 01 - Speak to Me.opus
│       ├── 01 - Speak to Me.lrc
│       ├── 02 - Breathe.opus
│       ├── 02 - Breathe.lrc
│       └── cover.jpg
│
├── Radiohead/
│   └── 1997 - OK Computer/
│       ├── 01 - Airbag.opus
│       ├── 01 - Airbag.lrc
│       ├── 02 - Paranoid Android.opus
│       ├── 02 - Paranoid Android.lrc
│       └── cover.jpg
│
└── _Playlists/
    ├── My Favorites [n2g-XhDv].m3u
    └── My Favorites [n2g-XhDv].jpg
```

When downloading a playlist, each track goes to its album folder—the M3U file just references them:

```m3u
#EXTM3U
#EXTINF:239,Pink Floyd - Breathe
../Pink Floyd/1973 - The Dark Side of the Moon/02 - Breathe.opus
#EXTINF:386,Radiohead - Paranoid Android
../Radiohead/1997 - OK Computer/02 - Paranoid Android.opus
```

## ✨ Features

- **Web UI** — Real-time progress, job queue, responsive design
- **Albums, playlists & tracks** — Paste any YouTube Music link, get organized files
- **Scheduled sync** — Subscribe to playlists; new tracks download automatically
- **Smart deduplication** — Same track across 10 playlists? Stored once, referenced everywhere
- **Reliable downloads** — Automatic retry on failures, graceful cancellation
- **Automatic lyrics** — Synced `.lrc` files downloaded alongside tracks when available
- **ReplayGain tagging** — Track and album ReplayGain/R128 tags for consistent playback volume
- **Format options** — Native `opus` (best quality), mp3, or m4a (direct download when available, transcoded otherwise)
- **Media server ready** — Tested with [Navidrome, Jellyfin, and Gonic](#-media-server-integration)
- **[CLI](packages/yubal/src/yubal/cli/README.md)** — Download and inspect metadata from the terminal

## 🧩 Browser Extension

Download tracks and subscribe to playlists directly from YouTube and YouTube Music without leaving the page.

<p>
  <img src="https://raw.githubusercontent.com/guillevc/yubal/refs/heads/master/extension/docs/images/extension-track.png" alt="Track view" width="32%">
  <img src="https://raw.githubusercontent.com/guillevc/yubal/refs/heads/master/extension/docs/images/extension-playlist.png" alt="Playlist view" width="32%">
  <img src="https://raw.githubusercontent.com/guillevc/yubal/refs/heads/master/extension/docs/images/extension-settings.png" alt="Settings view" width="32%">
</p>
<p>
  <a href="https://addons.mozilla.org/addon/yubal/"><img src="https://img.shields.io/badge/Firefox-get_add--on-FF7139?logo=firefox&logoColor=white&style=for-the-badge" alt="Get the add-on for Firefox"></a>
  <a href="https://github.com/guillevc/yubal/releases?q=🧩"><img src="https://img.shields.io/badge/Chrome-manual_install-4285F4?logo=googlechrome&logoColor=white&style=for-the-badge" alt="Chrome manual install"></a>
</p>

More info in the extension's [README.md](https://github.com/guillevc/yubal/blob/master/extension/README.md).

## 🚀 Quick Start

```yaml
# compose.yaml
services:
  yubal:
    image: ghcr.io/guillevc/yubal:latest
    container_name: yubal
    user: 1000:1000
    ports:
      - 8000:8000
    environment:
      YUBAL_SCHEDULER_CRON: "0 0 * * *"
      YUBAL_DOWNLOAD_UGC: false
      YUBAL_TZ: UTC
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    restart: unless-stopped
```

> [!TIP]
> **Volume permissions:** The container runs as UID:GID `1000:1000` by default. If your host user has a different UID, either:
>
> - Change `user:` to match your UID:GID (run `id` to check), or
> - Set ownership on the volume directories: `chown 1000:1000 -R data config`

```bash
docker compose up -d
# Open http://localhost:8000
```

> **Unraid?** Use the [community Docker template](https://github.com/SerpentDrago/UnraidDockerTemplates/tree/main/yubal) by [@SerpentDrago](https://github.com/SerpentDrago) ([unraid forum thread](https://forums.unraid.net/topic/197157-support-yubal-self-hosted-youtube-music-downloader/)).

## ⚙️ Configuration

| Variable                    | Description                                       | Default (Docker) |
| --------------------------- | ------------------------------------------------- | ---------------- |
| `YUBAL_AUDIO_FORMAT`        | `opus`, `mp3`, or `m4a`                           | `opus`           |
| `YUBAL_AUDIO_QUALITY`       | Transcode quality (0=best, 10=worst)              | `0`              |
| `YUBAL_SCHEDULER_ENABLED`   | Enable automatic scheduled sync                   | `true`           |
| `YUBAL_SCHEDULER_CRON`      | Cron schedule for auto-sync                       | `0 0 * * *`      |
| `YUBAL_FETCH_LYRICS`        | Fetch lyrics from lrclib.net                      | `true`           |
| `YUBAL_DOWNLOAD_UGC`        | Download user-generated content to `_Unofficial/` | `false`          |
| `YUBAL_REPLAYGAIN`          | Apply ReplayGain tags to downloads                | `true`           |
| `YUBAL_JOB_TIMEOUT_SECONDS` | Job execution timeout in seconds                  | `1800`           |
| `YUBAL_TZ`                  | Timezone (IANA format)                            | `UTC`            |

<details>
<summary>All options</summary>

| Variable                | Description                         | Default (Docker) |
| ----------------------- | ----------------------------------- | ---------------- |
| `YUBAL_HOST`            | Server bind address                 | `127.0.0.1`      |
| `YUBAL_PORT`            | Server port                         | `8000`           |
| `YUBAL_DATA`            | Music library output                | `/app/data`      |
| `YUBAL_CONFIG`          | Config directory                    | `/app/config`    |
| `YUBAL_LOG_LEVEL`       | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO`           |
| `YUBAL_ASCII_FILENAMES` | Transliterate unicode to ASCII      | `false`          |
| `YUBAL_CORS_ORIGINS`    | Allowed CORS origins                | `["*"]`          |
| `YUBAL_TEMP`            | Temp directory                      | System temp      |

</details>

## 🔌 Media Server Integration

Tested with Navidrome, Jellyfin, and Gonic. Artists link correctly, even on tracks with multiple artists.

| Server        | Artist linking                                                | Playlists |
| ------------- | ------------------------------------------------------------- | :-------: |
| **Navidrome** | ✅ Works out of the box                                       |    ✅     |
| **Jellyfin**  | ⚙️ Enable "Use non-standard artists tags" in library settings |    ✅     |
| **Gonic**     | ⚙️ Set `GONIC_MULTI_VALUE_ARTIST=multi`                       |    ❌     |

✅ Supported · ⚙️ Requires configuration · ❌ Not supported

<details>
<summary>Detailed setup guides</summary>

### Navidrome

No configuration required. Optionally, make imported playlists public:

```bash
ND_DEFAULTPLAYLISTPUBLICVISIBILITY=true
```

See [Navidrome docs](https://www.navidrome.org/docs/usage/configuration/options/).

### Jellyfin

For multi-artist support:

1. **Dashboard → Libraries → Music Library → Manage Library**
2. Check **Use non-standard artists tags**
3. Save and rescan

### Gonic

For artist linking:

```bash
GONIC_MULTI_VALUE_ARTIST=multi
GONIC_MULTI_VALUE_ALBUM_ARTIST=multi
```

M3U playlists are not supported ([pending PR](https://github.com/sentriz/gonic/pull/537)).

</details>

## 🍪 Cookies (Optional)

Need age-restricted content, private playlists, or Premium quality? Add your cookies:

1. Export `https://www.youtube.com/` cookies with a browser extension ([yt-dlp guide](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp))
2. Place at `config/ytdlp/cookies.txt` or upload via the web UI

> [!CAUTION]
> Cookie usage may trigger stricter rate limiting and could put your account at risk. See [#3](https://github.com/guillevc/yubal/issues/3) and [yt-dlp wiki](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#youtube).

## 🗺️ What's Coming

- [x] Playlist support with M3U generation ([v0.2.0](https://github.com/guillevc/yubal/releases/tag/v0.2.0))
- [x] Single track downloads ([v0.3.0](https://github.com/guillevc/yubal/releases/tag/v0.3.0))
- [x] Automatic lyrics (.lrc) ([v0.3.0](https://github.com/guillevc/yubal/releases/tag/v0.3.0))
- [x] Auto-sync playlists ([v0.4.0](https://github.com/guillevc/yubal/releases/tag/v0.4.0))
- [x] UGC tracks (user-generated content, remixes, unofficial tracks) ([v0.5.0](https://github.com/guillevc/yubal/releases/tag/v0.5.0))
- [x] Browser extension ([v0.7.0](https://github.com/guillevc/yubal/releases/tag/v0.7.0), [ext-v0.1.0](https://github.com/guillevc/yubal/releases/tag/ext-v0.1.0))
- [ ] Flat folder mode
- [ ] Post-download webhooks
- [ ] New music automatic discovery

## 💜 Support

If yubal is useful to you, consider supporting its development:

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/guillevc) [![Sponsor](https://img.shields.io/badge/sponsor-GitHub-ea4aaa?logo=github)](https://github.com/sponsors/guillevc)

A ⭐ also helps others discover yubal!

## 📈 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=guillevc/yubal&type=Date)](https://star-history.com/#guillevc/yubal&Date)

## 🙏 Acknowledgments

Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [ytmusicapi](https://github.com/sigma67/ytmusicapi).

Thanks to everyone who's starred, shared, reported bugs, suggested features, or [supported the project](https://ko-fi.com/guillevc) 💝

## License

[MIT](LICENSE)

---

<sub>For personal archiving only. Comply with YouTube's Terms of Service and applicable copyright laws.</sub>
