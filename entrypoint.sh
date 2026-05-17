#!/bin/bash
set -e

PUID=${PUID:-1000}
PGID=${PGID:-1000}

warn_chown() {
    path=$1
    echo "Warning: could not change ownership of '$path' to $PUID:$PGID; continuing because the mount may not support chown." >&2
}

ensure_writable() {
    path=$1

    if ! gosu "$PUID:$PGID" test -w "$path"; then
        echo "Error: '$path' is not writable by $PUID:$PGID. Set PUID/PGID to an account with write access to this mount." >&2
        exit 1
    fi
}

case "$PUID" in
    "" | *[!0-9]*)
        echo "PUID must be a numeric user id, got '$PUID'" >&2
        exit 1
        ;;
esac

case "$PGID" in
    "" | *[!0-9]*)
        echo "PGID must be a numeric group id, got '$PGID'" >&2
        exit 1
        ;;
esac

if [ "$(id -u)" = "0" ]; then
    # Create required directories
    mkdir -p /app/config/yubal /app/config/ytdlp /app/data

    # Fix ownership (non-recursive on /app/data to avoid slow startup with large libraries)
    chown "$PUID:$PGID" /app/data || warn_chown /app/data
    chown -R "$PUID:$PGID" /app/config
    ensure_writable /app/data

    exec gosu "$PUID:$PGID" "$@"
fi

# Non-root: still create dirs if possible, then exec
mkdir -p /app/config/yubal /app/config/ytdlp /app/data 2>/dev/null || true
exec "$@"
