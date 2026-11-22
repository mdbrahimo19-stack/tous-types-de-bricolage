# Image de production du backend Django (servi par gunicorn derrière Caddy).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Fichiers statiques (admin, DRF) rassemblés dans /app/staticfiles, servis par Caddy.
RUN DJANGO_DEBUG=False DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

# Utilisateur sans privilèges
RUN useradd --create-home --uid 1000 ttb && mkdir -p /app/media && chown -R ttb /app/media /app/staticfiles
USER ttb

EXPOSE 8000

# timeout 120 s : les appels à l'IA peuvent durer jusqu'à ~90 s
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--access-logfile", "-"]
