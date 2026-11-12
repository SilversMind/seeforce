"""
@c3:component
name: CLI Token Exchange
container: Backend
technology: Python / Django
description: Hands a signed-in browser session over to a local CLI — sends an unauthenticated caller through the GitHub login first, then mints the user's API token and redirects the browser to the port the CLI is listening on so the command line ends up authenticated without ever prompting for a password.
short_desc: Mints the API token and redirects it to the waiting local CLI
uses:
- Database/Database: "gets or creates the DRF auth token row for the signed-in user"
- SeeForce CLI/Login Command: "redirects the browser to the short-lived local callback server the command runs, carrying the token"
"""


from urllib.parse import urlencode

from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.http import require_GET
from rest_framework.authtoken.models import Token


@require_GET
def cli_auth(request):
    port = request.GET.get("port", "").strip()
    state = request.GET.get("state", "").strip()

    if not request.user.is_authenticated:
        next_url = request.get_full_path()
        return HttpResponseRedirect(f"/accounts/github/login/?{urlencode({'next': next_url})}")

    if not port or not port.isdigit():
        return HttpResponseBadRequest("Missing or invalid 'port' parameter.")

    token, _ = Token.objects.get_or_create(user=request.user)
    params = urlencode({"token": token.key, "state": state})
    return HttpResponseRedirect(f"http://localhost:{port}/callback?{params}")
