#!/bin/sh
set -e

# Ensure the data dir exists and is writable
mkdir -p /app/data
chown -R appuser:appuser /app/data || true

# Concurrency and port (Render provides $PORT)
: "${WEB_CONCURRENCY:=1}"
: "${PORT:=8000}"

# Start the app as the unprivileged user
exec gosu appuser:appuser gunicorn -w "$WEB_CONCURRENCY" -b "0.0.0.0:${PORT}" wsgi:app
