#!/usr/bin/env bash
set -euo pipefail

# Build frontend
cd frontend
npm ci
npm run build
cd ..

# Install backend deps and run Django setup
cd backend

# Service previews copy prod's env vars verbatim, so the settings module is switched here.
# NOTE: this must precede migrate, which would otherwise run against the production database.
if [ "${IS_PULL_REQUEST:-false}" = "true" ]; then
    export DJANGO_SETTINGS_MODULE=c4_project.settings.preview
fi

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
# Site domain for allauth redirects: a preview's own host, production's ALLOWED_HOSTS.
python manage.py shell -c "
from django.contrib.sites.models import Site
import os
if os.environ.get('IS_PULL_REQUEST') == 'true':
    domain = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
else:
    domain = os.environ.get('ALLOWED_HOSTS', 'seeforce.io').split(',')[0].strip()
if domain:
    Site.objects.update_or_create(id=1, defaults={'domain': domain, 'name': domain})
"

# A preview's host is not in the GitHub OAuth app, so /admin/ is the only way in.
if [ "${IS_PULL_REQUEST:-false}" = "true" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    # Non-zero simply means the user already exists on a rebuild of the same preview.
    python manage.py createsuperuser --noinput \
        --username "${DJANGO_SUPERUSER_USERNAME:-preview}" \
        --email "${DJANGO_SUPERUSER_EMAIL:-preview@example.invalid}" || true
fi
