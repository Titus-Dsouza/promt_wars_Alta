FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY frontend/ /app/frontend/

# Build a manifest with production static storage; these build-only values are
# not persisted as Docker ENV settings and contain no credentials.
RUN DJANGO_SECRET_KEY=build-only-placeholder \
    DEBUG=False \
    ALLOWED_HOSTS=localhost \
    DATABASE_URL=postgresql://build:build@127.0.0.1:5432/build \
    python manage.py collectstatic --noinput

RUN useradd --create-home --uid 10001 appuser
USER 10001

CMD ["sh", "-c", "exec gunicorn mediscribe.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 60"]
