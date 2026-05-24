FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist/ ./frontend_build/
RUN mkdir -p ./templates && cp ./frontend_build/index.html ./templates/index.html
RUN python manage.py collectstatic --noinput
EXPOSE 8000
CMD python manage.py migrate && \
    python seed_data.py && \
    gunicorn core.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 2