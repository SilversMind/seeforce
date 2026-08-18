#!/usr/bin/env bash
set -euo pipefail

# Install uv if not available
if ! command -v uv &>/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

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
