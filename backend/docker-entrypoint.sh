#!/usr/bin/env sh
# Entrypoint for the fexo-backend container: run one-off startup tasks then
# hand off to gunicorn. Runs on every container start (Render restarts the
# container on every deploy), so migrate/collectstatic re-run each time —
# both are idempotent so that's safe.
set -e

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Backfilling any missing media files..."
python manage.py backfill_missing_media

echo "Ensuring admin superuser..."
python manage.py ensure_superuser

# Render (and most PaaS hosts) inject $PORT and expect the process to bind
# to it; default to 8000 for local docker-compose / plain `docker run`.
echo "Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn fexo_project.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
