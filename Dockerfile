# AccessDocDemo — image build only prepares the codebase (no DB, no running servers).
# Runtime: use docker-compose (web = Gunicorn, worker = Celery only via entrypoint).

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ACCESSDOC_REPO_ROOT=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    tesseract-ocr \
    libglib2.0-0 \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY demo_docs/package.json demo_docs/package-lock.json ./demo_docs/
RUN cd demo_docs && npm ci

COPY backend/requirements.txt ./backend/
RUN python -m pip install --no-cache-dir -r backend/requirements.txt

COPY backend ./backend
COPY demo_docs ./demo_docs
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app/backend

ARG DJANGO_SECRET_KEY=docker-build-collectstatic-only
ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY} \
    DJANGO_DEBUG=false \
    DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
RUN python manage.py collectstatic --noinput

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
# Overridden for worker containers via ACCESSDOC_CONTAINER_ROLE=worker (entrypoint ignores CMD).
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "accessdoc.wsgi:application"]
