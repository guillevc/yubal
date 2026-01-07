#!/bin/sh
set -e

# Sync beets config (version-aware)
python /app/scripts/sync-beets-config.py

exec "$@"
