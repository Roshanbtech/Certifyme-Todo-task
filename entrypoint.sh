#!/bin/sh
set -e

# Ensure the data directory exists and is writable
mkdir -p /app/data
chown -R appuser:appuser /app/data

# Start the app as the unprivileged user
exec gosu appuser:appuser gunicorn -w 1 -b 0.0.0.0:8000 wsgi:app
