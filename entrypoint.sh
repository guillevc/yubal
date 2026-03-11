#!/bin/bash
set -e

PUID=${PUID:-1000}
PGID=${PGID:-1000}

if [ "$(id -u)" = "0" ]; then
    # Update yubal UID/GID if customized
    [ "$(id -u yubal)" != "$PUID" ] && usermod -u "$PUID" yubal
    [ "$(id -g yubal)" != "$PGID" ] && groupmod -g "$PGID" yubal

    # Create required directories
    mkdir -p /app/config/yubal /app/config/ytdlp /app/data

    # Fix ownership (non-recursive on /app/data to avoid slow startup with large libraries)
    chown yubal:yubal /app/data
    chown -R yubal:yubal /app/config

    exec gosu yubal "$@"
fi

# Non-root: still create dirs if possible, then exec
mkdir -p /app/config/yubal /app/config/ytdlp /app/data 2>/dev/null || true
exec "$@"
