# ── Stage 1: Build React frontend ──────────────────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend ─────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app/backend

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./

COPY --from=frontend-build /app/frontend/dist/ ./frontend_build/
RUN mkdir -p ./templates && cp ./frontend_build/index.html ./templates/index.html
RUN python manage.py collectstatic --noinput

COPY entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["sh", "./entrypoint.sh"]