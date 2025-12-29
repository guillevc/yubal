# Build args for version info
ARG COMMIT_SHA=dev
ENV COMMIT_SHA=$COMMIT_SHA

# Build frontend
FROM oven/bun:1-alpine AS web
WORKDIR /app/web
COPY web/package.json web/bun.lock ./
RUN bun install --frozen-lockfile
COPY web/ ./
RUN bun run build

# Deno binary (for yt-dlp)
FROM denoland/deno:bin AS deno

# Builder - install Python deps
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-cache

# Runtime
FROM python:3.12-slim-bookworm
WORKDIR /app

ARG TARGETARCH

# Install ffmpeg (johnvansickle static)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl xz-utils \
    && FFMPEG_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64" || echo "amd64") \
    && curl -L "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-${FFMPEG_ARCH}-static.tar.xz" \
       | tar -xJ --strip-components=1 -C /usr/local/bin/ --wildcards '*/ffmpeg' '*/ffprobe' \
    && apt-get purge -y curl xz-utils \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=deno /deno /usr/local/bin/deno
COPY --from=builder /app/.venv /app/.venv
COPY --from=web /app/web/dist ./web/dist
COPY yubal/ ./yubal/
COPY beets/config.yaml ./beets/config.yaml

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    YUBAL_HOST=0.0.0.0 \
    YUBAL_PORT=8000 \
    YUBAL_DATA_DIR=/app/data \
    YUBAL_BEETS_DIR=/app/beets \
    YUBAL_YTDLP_DIR=/app/ytdlp

EXPOSE 8000

CMD ["python", "-m", "yubal"]
