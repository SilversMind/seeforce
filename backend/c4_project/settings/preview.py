"""Render preview settings: production hardening on a throwaway sqlite database."""

import os

from .prod import *

# NOTE: previews inherit prod's DATABASE_URL, so dropping this makes build.sh migrate production.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Preview URLs are public and guessable, so gate everything before Django routes it.
MIDDLEWARE = ["c4_project.preview_auth.basic_auth_middleware", *MIDDLEWARE]

# A preview's hostname is assigned by Render, so the values copied from prod are wrong.
_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
if _host:
    ALLOWED_HOSTS = [_host]
    CORS_ALLOWED_ORIGINS = [f"https://{_host}"]
    LOGIN_REDIRECT_URL = f"https://{_host}/"
