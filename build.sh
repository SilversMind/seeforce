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
