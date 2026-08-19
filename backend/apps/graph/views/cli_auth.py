from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.http import require_GET
from rest_framework.authtoken.models import Token
from urllib.parse import urlencode


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
