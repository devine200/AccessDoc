#!/bin/sh
set -e
cd /app/backend
mkdir -p media templates/doc_builds
python manage.py migrate --noinput

# Dedicated worker container: Celery only (no Gunicorn, no dev superuser).
if [ "${ACCESSDOC_CONTAINER_ROLE:-web}" = "worker" ]; then
  exec celery -A accessdoc worker -l info --concurrency="${CELERY_WORKER_CONCURRENCY:-1}"
fi

# Single-container deploy (e.g. one Railway service): run a Celery consumer alongside Gunicorn.
# Do not use with a separate worker service or tasks may be processed twice.
if [ "${ACCESSDOC_EMBEDDED_CELERY_WORKER:-}" = "1" ]; then
  celery -A accessdoc worker -l info --concurrency="${CELERY_WORKER_CONCURRENCY:-1}" &
fi

# web (default)
if [ "${SKIP_DEFAULT_SUPERUSER:-}" != "1" ] && [ "${SKIP_DEFAULT_SUPERUSER:-}" != "true" ]; then
  DJANGO_SUPERUSER_USERNAME=admin \
  DJANGO_SUPERUSER_EMAIL=admin@localhost \
  DJANGO_SUPERUSER_PASSWORD=admin \
  python manage.py createsuperuser --noinput || true
fi

exec "$@"
