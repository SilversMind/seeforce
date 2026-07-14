import os

from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CORS_ALLOW_ALL_ORIGINS = True
