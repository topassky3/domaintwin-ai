#!/bin/sh
set -eu

mode="${1:-web}"

if [ "$mode" = "web" ]; then
  echo "[DomainTwin] applying database migrations"
  python manage.py migrate --noinput
  echo "[DomainTwin] starting gunicorn"
  exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT_SECONDS:-30}" \
    --access-logfile - \
    --error-logfile -
fi

if [ "$mode" = "monitor" ]; then
  echo "[DomainTwin] waiting for database migrations"
  until python manage.py migrate --check >/dev/null 2>&1; do
    sleep 2
  done
  echo "[DomainTwin] starting Monitoring Lite worker"
  exec python manage.py monitor_domaintwin --loop
fi

exec "$@"
