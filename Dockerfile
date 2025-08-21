FROM python:3.11-slim-bookworm

# Minimal, predictable runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Create unprivileged user and install 'gosu' to drop root at runtime
RUN adduser --disabled-password --gecos "" appuser \
    && apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (better layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Prepare data dir and script perms
RUN mkdir -p /app/data \
    && chown -R appuser:appuser /app \
    && chmod +x /app/entrypoint.sh

# Persist DB between runs (works with named volumes)
VOLUME ["/app/data"]

EXPOSE 8000

# Fix ownership of the mounted volume at runtime, then drop privileges
ENTRYPOINT ["/app/entrypoint.sh"]
