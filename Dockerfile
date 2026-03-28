# AccessDocDemo: Node (Docusaurus) + Python (Django), Gunicorn
# Build context: repository root (contains backend/ and demo_docs/).

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

# 1) Docusaurus dependencies (pipeline runs npm in demo_docs at publish time)
COPY demo_docs/package.json demo_docs/package-lock.json ./demo_docs/
RUN cd demo_docs && npm ci

# 2) Python dependencies
COPY backend/requirements.txt ./backend/
RUN python -m pip install --no-cache-dir -r backend/requirements.txt

# 3) Application source
COPY backend ./backend
COPY demo_docs ./demo_docs
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app/backend

# 4) Django static files for WhiteNoise
ARG DJANGO_SECRET_KEY=docker-build-collectstatic-only
ENV DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY} \
    DJANGO_DEBUG=false \
    DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
RUN python manage.py collectstatic --noinput

# Default admin user is created in docker/entrypoint.sh (container start) via
# ``createsuperuser --noinput``, not in a RUN step here: the runtime DB/volume is not
# available at image build time.

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "accessdoc.wsgi:application"]
