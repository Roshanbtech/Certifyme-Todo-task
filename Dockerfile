FROM python:3.11-slim-bookworm

# minimal, secure runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# install python deps first (better cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app code
COPY . .

# non-root user + writable data dir for SQLite
RUN useradd -ms /bin/bash appuser && mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser

# default DB path inside container (your app already reads DATABASE_URL)
ENV DATABASE_URL=sqlite:///data/db.sqlite3

EXPOSE 8000
CMD ["gunicorn","-w","2","-b","0.0.0.0:8000","wsgi:app"]
