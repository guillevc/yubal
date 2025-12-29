# Build frontend
FROM oven/bun:1-alpine AS web
WORKDIR /app/web
COPY web/package.json web/bun.lock ./
RUN bun install --frozen-lockfile
COPY web/ ./
RUN bun run build

# Deno binary (for yt-dlp)
FROM denoland/deno:bin AS deno

# Runtime
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app

# Install runtime deps
RUN apt update \
  && apt install -y --no-install-recommends ffmpeg \
  && rm -rf /var/lib/apt/lists/*

# Copy deno binary
COPY --from=deno /deno /usr/local/bin/deno

# Install python deps
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

# Copy app
COPY yubal/ ./yubal/
COPY --from=web /app/web/dist ./web/dist
COPY beets/config.yaml ./beets/config.yaml

ENV YUBAL_HOST=0.0.0.0 \
    YUBAL_PORT=8000 \
    YUBAL_DATA_DIR=/app/data \
    YUBAL_BEETS_DIR=/app/beets \
    YUBAL_YTDLP_DIR=/app/ytdlp
EXPOSE 8000

CMD ["uv", "run", "python", "-m", "yubal"]
