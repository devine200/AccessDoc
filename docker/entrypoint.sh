#!/bin/sh
set -e
cd /app/backend
mkdir -p media templates/doc_builds
if [ -n "${ACCESSDOC_SQLITE_DIR:-}" ]; then
  mkdir -p "$ACCESSDOC_SQLITE_DIR"
fi
python manage.py migrate --noinput

# worker: only run Celery (no Gunicorn, no dev superuser). Build already set up the codebase.
if [ "${ACCESSDOC_CONTAINER_ROLE:-web}" = "worker" ]; then
  exec celery -A accessdoc worker -l info
fi

# web (default)
if [ "${SKIP_DEFAULT_SUPERUSER:-}" != "1" ] && [ "${SKIP_DEFAULT_SUPERUSER:-}" != "true" ]; then
  DJANGO_SUPERUSER_USERNAME=admin \
  DJANGO_SUPERUSER_EMAIL=admin@localhost \
  DJANGO_SUPERUSER_PASSWORD=admin \
  python manage.py createsuperuser --noinput || true
fi

exec "$@"
