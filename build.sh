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
python manage.py shell -c "
from django.contrib.sites.models import Site
import os
domain = os.environ.get('ALLOWED_HOSTS', 'seeforce.onrender.com').split(',')[0].strip()
if domain:
    Site.objects.update_or_create(id=1, defaults={'domain': domain, 'name': domain})
"
