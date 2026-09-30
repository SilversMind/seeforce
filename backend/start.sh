#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Service previews copy prod's env vars verbatim, so the settings module is switched here.
# NOTE: previewValue in render.yaml only reaches Pro preview environments, never a service preview.
if [ "${IS_PULL_REQUEST:-false}" = "true" ]; then
    export DJANGO_SETTINGS_MODULE=c4_project.settings.preview
fi

exec gunicorn c4_project.wsgi --workers 2 --bind "0.0.0.0:$PORT"
