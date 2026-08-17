from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session authentication that skips CSRF enforcement.

    Django's CsrfViewMiddleware is not in MIDDLEWARE, but DRF's
    SessionAuthentication calls enforce_csrf() independently on every
    authenticated POST. This subclass disables that check so that
    browser fetch() calls to POST endpoints work without X-CSRFToken.
    request.user is still populated from the Django session normally.
    """

    def enforce_csrf(self, request):
        return  # no-op: CSRF is handled at the network boundary (SameSite cookie)
