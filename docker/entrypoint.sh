#!/bin/sh
set -e
cd /app/backend
mkdir -p media templates/doc_builds
python manage.py migrate --noinput

# Dev superuser: Django's built-in CLI (not a custom command). Runs at container *start*
# so the database exists (bind mounts / volumes). Image *build* is the wrong place for this.
# ``--noinput`` fails if ``admin`` already exists; ``|| true`` keeps the entrypoint succeeding.
if [ "${SKIP_DEFAULT_SUPERUSER:-}" != "1" ] && [ "${SKIP_DEFAULT_SUPERUSER:-}" != "true" ]; then
  DJANGO_SUPERUSER_USERNAME=admin \
  DJANGO_SUPERUSER_EMAIL=admin@localhost \
  DJANGO_SUPERUSER_PASSWORD=admin \
  python manage.py createsuperuser --noinput || true
fi

exec "$@"
