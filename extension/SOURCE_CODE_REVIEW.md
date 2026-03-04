# Source Code Review Instructions

This document explains how to build the yubal browser extension from source
for add-on review purposes.

## Overview

yubal is a companion browser extension for [yubal](https://github.com/guillevc/yubal),
a self-hosted YouTube Music library manager. The extension sends YouTube URLs
from the browser to a user-configured yubal server instance.

- **Framework**: [WXT](https://wxt.dev/) (Web Extension Tools)
- **Language**: TypeScript
- **UI**: [van.js](https://vanjs.org/) (minimal reactive UI library)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) v4

Requires [Bun](https://bun.sh/) v1.3.6+.

## Build from Source

From the `extension/` directory:

```sh
# 1. Install dependencies
bun install --frozen-lockfile

# 2. Build for Chrome (Manifest V3)
bun run build

# 3. Build for Firefox
bun run build:firefox
```

Build output is written to:

- `.output/chrome-mv3/` — Chrome/Chromium build
- `.output/firefox-mv2/` — Firefox build

## Creating Distribution Zips

```sh
bun run zip            # Chrome zip
bun run zip:firefox    # Firefox zip
```

Zips are written to `.output/`.
