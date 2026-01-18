# Build frontend
FROM oven/bun:1-alpine AS web-builder

ARG VERSION=dev
ARG COMMIT_SHA=dev
ARG IS_RELEASE=false

WORKDIR /app/web
COPY web/package.json web/bun.lock ./
RUN bun install --frozen-lockfile

COPY web/ ./
RUN VITE_VERSION=$VERSION \
    VITE_COMMIT_SHA=$COMMIT_SHA \
    VITE_IS_RELEASE=$IS_RELEASE \
    bun run build

# Install Python dependencies
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS python-builder

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/

RUN uv sync --package yubal-api --no-dev --frozen --no-cache --no-editable

# Final runtime image
FROM python:3.12-slim-bookworm

ARG TARGETARCH

WORKDIR /app

# Install ffmpeg (static) + deno for yt-dlp
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl xz-utils unzip ca-certificates \
    && FFMPEG_ARCH=$([ "$TARGETARCH" = "arm64" ] && echo "arm64" || echo "amd64") \
    && curl -fsSL "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-${FFMPEG_ARCH}-static.tar.xz" \
       | tar -xJ --strip-components=1 -C /usr/local/bin/ --wildcards '*/ffmpeg' '*/ffprobe' \
    && curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh \
    && apt-get purge -y curl xz-utils unzip \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=python-builder /app/.venv /app/.venv
COPY --from=web-builder /app/web/dist ./web/dist

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    YUBAL_ROOT=/app \
    YUBAL_HOST=0.0.0.0 \
    YUBAL_PORT=8000

EXPOSE 8000

CMD ["python", "-m", "yubal_api"]
