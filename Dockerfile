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

# hadolint ignore=DL3008
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages/ ./packages/
RUN uv sync --package yubal-api --no-dev --frozen --no-cache --no-editable

# Final runtime image
FROM python:3.12-slim-bookworm

ARG TARGETARCH
ARG DENO_VERSION=2.6.3
ARG RSGAIN_VERSION=3.6

WORKDIR /app
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install runtime dependencies in a single layer:
#   1. ffmpeg (static binary)
#   2. deno (JS runtime for yt-dlp)
#   3. rsgain (ReplayGain tagger, amd64 only)
#   4. Cleanup temp packages
#   5. Create non-root user
# hadolint ignore=DL3008
RUN set -eux \
    # --- Temp build deps ---
    && apt-get update \
    && apt-get install -y --no-install-recommends curl xz-utils unzip ca-certificates \
    #
    # --- ffmpeg (static) ---
    && curl -fsSL --retry 3 --retry-delay 5 -o /tmp/ffmpeg.tar.xz \
       "https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-${TARGETARCH}-static.tar.xz" \
    && tar -xJf /tmp/ffmpeg.tar.xz --strip-components=1 -C /usr/local/bin/ \
       --wildcards '*/ffmpeg' '*/ffprobe' \
    && rm /tmp/ffmpeg.tar.xz \
    #
    # --- deno (for yt-dlp) ---
    && curl -fsSL https://deno.land/install.sh | DENO_INSTALL=/usr/local sh -s v${DENO_VERSION} \
    #
    # --- rsgain (amd64 only) ---
    && if [ "$TARGETARCH" = "amd64" ]; then \
         curl -fsSL --retry 3 --retry-delay 5 -o /tmp/rsgain.deb \
           "https://github.com/complexlogic/rsgain/releases/download/v${RSGAIN_VERSION}/rsgain_${RSGAIN_VERSION}_amd64.deb" \
         && (dpkg -i /tmp/rsgain.deb || apt-get install -y -f --no-install-recommends) \
         && rm /tmp/rsgain.deb; \
       fi \
    #
    # --- Cleanup ---
    && apt-get purge -y curl xz-utils unzip \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    #
    # --- Non-root user ---
    && groupadd -g 1000 yubal \
    && useradd -u 1000 -g yubal -d /app -s /sbin/nologin yubal

# Copy built artifacts
COPY --from=python-builder --chown=yubal:yubal /app/.venv /app/.venv
COPY --from=web-builder --chown=yubal:yubal /app/web/dist ./web/dist

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    YUBAL_ROOT=/app \
    YUBAL_HOST=0.0.0.0 \
    YUBAL_PORT=8000

USER yubal
EXPOSE 8000
CMD ["python", "-m", "yubal_api"]
