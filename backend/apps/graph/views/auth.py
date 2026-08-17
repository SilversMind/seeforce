"""
@c3:component
name: Auth API
container: Backend
description: Exposes /api/auth/me/ and /api/auth/logout/; delegates GitHub OAuth flow to django-allauth
uses:
  - GitHub: "OAuth 2.0 login and identity resolution"
    technology: HTTPS
"""

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
    return Response({
        "id": request.user.id,
        "username": request.user.username,
        "avatar_url": avatar_url,
    })


@api_view(["POST"])
def auth_logout(request):
    if not request.user.is_authenticated:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    django_logout(request)
    return Response({"ok": True})
