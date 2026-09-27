"""
@c3:component
name: GitHub App Setup Endpoint
container: Backend
description: Receives GitHub's post-install/post-update redirect, verifies with GitHub that the installation belongs to the logged-in user's own GitHub account, and links the installation_id to that SeeForce user.
short_desc: Handles GitHub's post-install redirect and links the installation
uses:
  - GitHub App Token Manager: "Reads the installation's owning GitHub account to verify the caller actually performed this installation"
  - Database: "creates or updates the GitHubAppInstallation row for the logged-in user"
"""
from urllib.parse import urlencode

from django.conf import settings
from django.http import (
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
)
from django.views.decorators.http import require_GET

from ..github_app import GitHubAppTokenManager
from ..models import GitHubAppInstallation


@require_GET
def github_app_setup(request):
    if not request.user.is_authenticated:
        next_url = request.get_full_path()
        return HttpResponseRedirect(f"/accounts/github/login/?{urlencode({'next': next_url})}")

    installation_id = request.GET.get("installation_id", "").strip()
    if not installation_id:
        return HttpResponseBadRequest("Missing 'installation_id' parameter.")

    # installation_id is attacker-supplied and enumerable — ask GitHub who owns
    # it and only claim it for the matching SeeForce user.
    social = request.user.socialaccount_set.filter(provider="github").first()
    if social is None:
        return HttpResponseForbidden("No GitHub account is linked to this SeeForce account.")

    account = GitHubAppTokenManager().installation_account(installation_id)
    if not account:
        return HttpResponseBadRequest("Unknown GitHub App installation.")

    # ponytail: only installs on the user's *own* GitHub account can be verified
    # with app-JWT auth — an org install's account is the org, so it is rejected.
    # Upgrade path: GET /user/installations with a user-to-server token.
    account_login = account.get("login") or ""
    if str(account.get("id")) != str(social.uid) and (
        account_login.lower() != (social.extra_data.get("login") or "").lower()
    ):
        return HttpResponseForbidden(
            "This GitHub App installation belongs to a different GitHub account."
        )

    GitHubAppInstallation.objects.update_or_create(
        installation_id=installation_id,
        defaults={"user": request.user, "account_login": account_login},
    )
    return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
