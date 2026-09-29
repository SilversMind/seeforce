#!/usr/bin/env bash
set -euo pipefail

# Build frontend
cd frontend
npm ci
npm run build
cd ..

# Install backend deps and run Django setup
cd backend
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
# Set site domain for allauth OAuth redirect URI
# Only a preview reads RENDER_EXTERNAL_HOSTNAME: its ALLOWED_HOSTS is copied from the
# base service and still names production. Production keeps using ALLOWED_HOSTS, which
# may be a custom domain that RENDER_EXTERNAL_HOSTNAME would wrongly override.
python manage.py shell -c "
from django.contrib.sites.models import Site
import os
if os.environ.get('IS_PULL_REQUEST') == 'true':
    domain = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
else:
    domain = os.environ.get('ALLOWED_HOSTS', 'seeforce.onrender.com').split(',')[0].strip()
if domain:
    Site.objects.update_or_create(id=1, defaults={'domain': domain, 'name': domain})
"

# A preview starts from an empty sqlite database and its hostname is not registered
# with the GitHub OAuth app, so social login cannot work there. Seed a superuser
# instead: log in at /admin/ and the session cookie unlocks the API and the SPA.
if [ "${IS_PULL_REQUEST:-false}" = "true" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    # Non-zero simply means the user already exists on a rebuild of the same preview.
    python manage.py createsuperuser --noinput \
        --username "${DJANGO_SUPERUSER_USERNAME:-preview}" \
        --email "${DJANGO_SUPERUSER_EMAIL:-preview@example.invalid}" || true
fi
