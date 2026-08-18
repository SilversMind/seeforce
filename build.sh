#!/usr/bin/env bash
set -euo pipefail

# Install uv and ensure we use the real binary, not Render's broken wrapper
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

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
