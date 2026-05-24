# ── Stage 1: Build React frontend ──────────────────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app

# Copy both dirs so vite plugin can write to ../backend/
COPY frontend/ ./frontend/
COPY backend/ ./backend/

WORKDIR /app/frontend
RUN npm install && npm run build
# After build:
#   /app/backend/frontend_build/       ← Vite output
#   /app/backend/templates/index.html  ← copied by vite plugin

# ── Stage 2: Python backend ─────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

# Pull in frontend artifacts from stage 1
COPY --from=frontend-build /app/backend/frontend_build ./frontend_build
COPY --from=frontend-build /app/backend/templates ./templates

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD python manage.py migrate && \
    python seed_data.py && \
    gunicorn core.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2