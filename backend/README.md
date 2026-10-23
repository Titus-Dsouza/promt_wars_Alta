# MediScribe Backend

Django API and server-side Google Gemini 3.8 Flash integration using the official `google-genai` SDK. The intended model defaults to `gemini-3.8-flash` and can be changed with `GEMINI_MODEL`.

## Local development

```sh
cp .env.example .env
# Set GEMINI_API_KEY in backend/.env to enable live generation.
../.venv/bin/python manage.py check
../.venv/bin/python manage.py test
../.venv/bin/python manage.py runserver 127.0.0.1:8000
```

No live API key is needed to start Django or run mocked tests. Without a key, AI generation returns an explicit unavailable state and does not invent a report.

## Configuration

See `.env.example`. Credentials belong in the ignored `backend/.env` file locally or a secret manager at deployment. Never place them in frontend files, logs, or Git.

Production requires `DEBUG=False`, a strong `DJANGO_SECRET_KEY`, explicit `ALLOWED_HOSTS`, `DATABASE_URL` for a persistent PostgreSQL database, and `GEMINI_API_KEY`. Set `CSRF_TRUSTED_ORIGINS` only for the deployed site origins when cross-origin POSTs are actually needed. The configured model is `GEMINI_MODEL=gemini-3.8-flash` unless deliberately overridden.

## Cloud Run

The repository root `Dockerfile` builds the Django WSGI app with Gunicorn. Configure the variables above in Cloud Run and use Secret Manager for the Django secret and Gemini API key. Provide a PostgreSQL URL for persistent sessions/admin data, then run `python manage.py migrate` once as a release task before routing traffic. Configure the `/health/` endpoint as the HTTP health check. Static files are collected during image build and served by WhiteNoise.

The container listens on Cloud Run's `PORT` and uses the production WSGI entry point, `mediscribe.wsgi:application`. Deployment itself must be performed and verified separately.
