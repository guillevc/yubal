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

## Prerequisites

- [Bun](https://bun.sh/) v1.3.6+ (preferred)
- Or [Node.js](https://nodejs.org/) v22+ and npm v10+

## Build from Source

From the root of the extracted sources:

### Using Bun (preferred)

```sh
# 1. Install dependencies
bun install --frozen-lockfile

# 2. Build for Firefox
bun run build:firefox
```

### Using npm (alternative)

```sh
# 1. Install dependencies
npm install --legacy-peer-deps

# 2. Build for Firefox
npm run build:firefox
```

## Build Output

Build output is written to `.output/firefox-mv2/`.

The generated files should match the contents of the submitted extension zip.
