#!/bin/sh
set -e
echo "Running migrations..."
python manage.py migrate --noinput
echo "Seeding data..."
python seed_data.py
echo "Starting gunicorn..."
exec gunicorn core.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120