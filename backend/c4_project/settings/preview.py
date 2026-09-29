"""Settings for Render pull request previews: production hardening, throwaway database.

A Render service preview copies every environment variable from its base service,
DATABASE_URL included, so the database has to be overridden here explicitly. Without
that override, build.sh's `manage.py migrate` would run against production on every
preview build.

The sqlite file is created during the build and ships with the image, so a preview
boots already migrated. Render's free instances have an ephemeral filesystem: the
database resets whenever the instance spins down (15 minutes without traffic) and
comes back empty but migrated. A preview is disposable by design — re-scan after a
pause rather than expecting state to survive.
"""

import os

from .prod import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# A preview's hostname is assigned by Render, so the values copied from prod are wrong.
_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
if _host:
    ALLOWED_HOSTS = [_host]
    CORS_ALLOWED_ORIGINS = [f"https://{_host}"]
    LOGIN_REDIRECT_URL = f"https://{_host}/"
