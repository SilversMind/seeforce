"""
@c3:component
name: Auth API
container: Backend
description: Exposes /api/auth/me/ and /api/auth/logout/; delegates GitHub OAuth flow to django-allauth, reports whether the user has a GitHub App installation, and hands back the GitHub App's install/configure URL
uses:
  - GitHub: "OAuth 2.0 login and identity resolution"
    technology: HTTPS
  - Database: "reads the user's GitHub SocialAccount and GitHubAppInstallation rows"
"""

import os

from django.contrib.auth import logout as django_logout
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(["GET"])
def auth_me(request):
    if not request.user.is_authenticated:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    social = request.user.socialaccount_set.filter(provider="github").first()
    avatar_url = social.extra_data.get("avatar_url", "") if social else ""
    # GitHub redirects installations/new straight to the "configure" screen when
    # the app is already installed for the current account — one URL for both.
    app_slug = os.environ.get("GITHUB_APP_SLUG", "")
    install_url = f"https://github.com/apps/{app_slug}/installations/new" if app_slug else None
    return Response({
        "id": request.user.id,
        "username": request.user.username,
        "avatar_url": avatar_url,
        # Repo access comes from a GitHub App installation, not the login token.
        "github_app_installed": request.user.github_app_installations.exists(),
        "github_app_install_url": install_url,
    })


@api_view(["POST"])
def auth_logout(request):
    if not request.user.is_authenticated:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    django_logout(request)
    return Response({"ok": True})
