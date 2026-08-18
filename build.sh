#!/usr/bin/env bash
set -euo pipefail

# Build frontend
cd frontend
npm ci
npm run build
cd ..

# Install backend deps
cd backend
uv sync
uv run python manage.py collectstatic --no-input
uv run python manage.py migrate
