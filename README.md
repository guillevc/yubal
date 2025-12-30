<div align="center">

# yubal

**YouTube album downloader with Spotify metadata auto-tagging.**
<br/>
_Powered by yt-dlp and beets._

[![CI Status](https://github.com/guillevc/yubal/actions/workflows/ci.yaml/badge.svg)](https://github.com/guillevc/yubal/actions/workflows/ci.yaml)
[![GitHub Release](https://img.shields.io/github/v/release/guillevc/yubal)](https://github.com/guillevc/yubal/releases)
[![Docker Image](https://img.shields.io/badge/ghcr.io-blue?logo=docker&logoColor=white)](https://ghcr.io/guillevc/yubal)
[![License: MIT](https://img.shields.io/badge/License-MIT-white)](LICENSE)

<picture>
  <img src="docs/demo.gif" alt="Yubal Demo Interface" width="600">
</picture>

</div>

## 📖 Overview

**yubal** is a self-hosted web application that streamlines the process of building a local music library. Simply paste a YouTube Music album URL, and Yubal orchestrates a background pipeline to download the audio and apply high-quality metadata tags automatically.

### The Pipeline

```
                                 ┌──────────┐
                ┌─────────┐      │ Spotify  │
                │ YouTube │      │ metadata │
                └──────▲──┘      └──▲───────┘
                       │            │
                    ┌──────────────────┐
                    │       yubal      │──────► /Artist/Year - Album
YouTube Music ─────►│                  │        ├─01 - Track.opus
  Album URLs        │ (yt-dlp + beets) │        ├─02 - Track.opus
                    └──────────────────┘        ├─...
                                                └─cover.jpg
```

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp):** Downloads highest available quality audio streams from YouTube.
- **[beets](https://beets.io):** Handles auto-tagging using Spotify metadata and ensures correct album art embedding.

## ✨ Features

- **Web Interface:** Clean, responsive UI for submitting albums and monitoring real-time progress.
- **Job Queue:** Integrated FIFO queue that processes downloads sequentially to ensure reliability and avoid rate limiting.
- **Smart Auto-tagging:** Automatic metadata fetching via beets, enriched by Spotify's metadata for accurate tracklists and art.
- **Format Configuration:** Optimized for `opus` (native YouTube quality), with optional transcoding for other formats.

## 🚀 Quick Start

The recommended way to run **yubal** is via Docker Compose.

### 1. Create a `compose.yaml`

```yaml
services:
  yubal:
    image: ghcr.io/guillevc/yubal:latest
    container_name: yubal
    ports:
      - "8000:8000"
    environment:
      - YUBAL_TZ=UTC
      # Check the Configuration section for more variables
    volumes:
      - ./data:/app/data # Where your music will be saved
      - ./beets:/app/beets # Beets configuration and database
      - ./ytdlp:/app/ytdlp # yt-dlp configuration (cookies)
    restart: unless-stopped
```

### 2. Run the container

```bash
docker compose up -d

```

### 3. Start Downloading

Open your browser to `http://localhost:8000` and paste a YouTube Music album URL.

> [!TIP]
> **Premium Quality & Age Restrictions**
> To download age-restricted content or access higher bitrate audio (for Premium accounts), you must provide cookies:
>
> 1. Export your cookies using a browser extension. [See yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
> 2. Save the file as `cookies.txt`.
> 3. Place it in your mounted `ytdlp` volume (or upload via the Web UI).

## ⚙️ Configuration

yubal is configured via Environment Variables.

| Variable              | Description                              | Default (Docker) |
| --------------------- | ---------------------------------------- | ---------------- |
| `YUBAL_HOST`          | Server bind address                      | `0.0.0.0`        |
| `YUBAL_PORT`          | Server listening port                    | `8000`           |
| `YUBAL_DATA_DIR`      | Destination for tagged music             | `/app/data`      |
| `YUBAL_BEETS_DIR`     | Location of beets db and config          | `/app/beets`     |
| `YUBAL_YTDLP_DIR`     | Location of cookies.txt                  | `/app/ytdlp`     |
| `YUBAL_AUDIO_FORMAT`  | Output audio codec (e.g., `opus`, `mp3`) | `opus`           |
| `YUBAL_AUDIO_QUALITY` | Transcoding quality (VBR scale 0-9)      | `0` (Best)       |
| `YUBAL_TZ`            | Timezone (IANA format)                   | `UTC`            |

> [!NOTE]
> **Audio Transcoding**
> By default, yubal keeps the original `opus` stream from YouTube to maintain maximum quality and processing speed. Transcoding only occurs if you change `YUBAL_AUDIO_FORMAT` or if the source is not natively available in your chosen format.

## 🤝 Acknowledgments

- **Color Scheme:** [Flexoki](https://stephango.com/flexoki) by Steph Ango.
- **Core Tools:** This project would not be possible without [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [beets](https://github.com/beetbox/beets).

## 📄 License

This project is licensed under the [MIT License](https://www.google.com/search?q=LICENSE).

## ⚠️ Disclaimer

This software is provided for **personal archiving purposes only**. Users are responsible for complying with YouTube's Terms of Service and applicable copyright laws in their jurisdiction. The authors do not promote piracy and are not responsible for misuse of this software.
