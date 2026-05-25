#!/bin/sh
set -e
export DJANGO_SETTINGS_MODULE=core.settings
echo "Running migrations..."
python manage.py migrate --noinput
echo "Seeding data..."
python seed_data.py
echo "Starting gunicorn on port ${PORT:-8000}..."
exec gunicorn core.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --log-level info