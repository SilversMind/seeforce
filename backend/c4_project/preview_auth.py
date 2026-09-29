"""HTTP Basic gate used only by settings.preview."""

import base64
import hmac
import os

from django.http import HttpResponse

CHALLENGE = {"WWW-Authenticate": 'Basic realm="preview"'}


def basic_auth_middleware(get_response):
    """Locks a whole preview behind the browser's password prompt."""
    username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "preview")
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

    def middleware(request):
        if _authorized(request, username, password):
            return get_response(request)
        return HttpResponse(status=401, headers=CHALLENGE)

    return middleware


def _authorized(request, username, password):
    """Fails closed: an unset password locks the preview instead of opening it."""
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not password or not header.startswith("Basic "):
        return False
    try:
        sent_user, _, sent_password = base64.b64decode(header[6:]).decode().partition(":")
    except (ValueError, UnicodeDecodeError):
        return False
    # NOTE: compare_digest on both halves, so neither one leaks through timing.
    return hmac.compare_digest(sent_user, username) and hmac.compare_digest(sent_password, password)
