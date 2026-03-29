#!/bin/sh
set -e
cd /app/backend
mkdir -p media templates/doc_builds
python manage.py migrate --noinput

# Dedicated worker container: Celery only (no Gunicorn, no dev superuser).
if [ "${ACCESSDOC_CONTAINER_ROLE:-web}" = "worker" ]; then
  exec celery -A accessdoc worker -l info --concurrency="${CELERY_WORKER_CONCURRENCY:-1}"
fi

# Run Celery beside Gunicorn unless explicitly disabled (e.g. separate worker container).
_emb=$(printf '%s' "${ACCESSDOC_EMBEDDED_CELERY_WORKER:-}" | tr '[:upper:]' '[:lower:]')
case "$_emb" in
  0|false|no) ;;
  *)
    celery -A accessdoc worker -l info --concurrency="${CELERY_WORKER_CONCURRENCY:-1}" &
    ;;
esac

# web (default)
if [ "${SKIP_DEFAULT_SUPERUSER:-}" != "1" ] && [ "${SKIP_DEFAULT_SUPERUSER:-}" != "true" ]; then
  DJANGO_SUPERUSER_USERNAME=admin \
  DJANGO_SUPERUSER_EMAIL=admin@localhost \
  DJANGO_SUPERUSER_PASSWORD=admin \
  python manage.py createsuperuser --noinput || true
fi

exec "$@"
