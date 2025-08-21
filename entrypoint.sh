#!/usr/bin/env sh
set -euo pipefail

# Render sets PORT dynamically; default to 8000 for local
PORT="${PORT:-8000}"

# Ensure app & data are writable (handles first boot + attached Disk)
mkdir -p /app/data
chown -R appuser:appuser /app

# Start as unprivileged user
exec gosu appuser:appuser \
  gunicorn wsgi:app \
    --bind "0.0.0.0:${PORT}" \
    --workers "${WEB_CONCURRENCY:-1}" \
    --threads "${THREADS:-4}" \
    --timeout "${TIMEOUT:-60}"
