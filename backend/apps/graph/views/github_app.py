"""
@c3:component
name: GitHub App Setup Endpoint
container: Backend
description: Receives GitHub's post-install/post-update redirect and links the installation_id to the logged-in SeeForce user.
uses:
  - Database: "creates or updates the GitHubAppInstallation row for the logged-in user"
"""
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.http import require_GET

from ..models import GitHubAppInstallation


@require_GET
def github_app_setup(request):
    if not request.user.is_authenticated:
        next_url = request.get_full_path()
        return HttpResponseRedirect(f"/accounts/github/login/?{urlencode({'next': next_url})}")

    installation_id = request.GET.get("installation_id", "").strip()
    if not installation_id:
        return HttpResponseBadRequest("Missing 'installation_id' parameter.")

    GitHubAppInstallation.objects.update_or_create(
        installation_id=installation_id,
        defaults={"user": request.user},
    )
    return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
