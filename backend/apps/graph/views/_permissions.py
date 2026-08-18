from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import BasePermission
from rest_framework.response import Response


class IsAuthenticatedOrReturn401(BasePermission):
    """Like IsAuthenticated but raises 401 (not 403) for anonymous requests."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            raise NotAuthenticated()
        return True


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


def _require_auth(request):
    if not request.user.is_authenticated:
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    return None


def _require_owner(request, pm):
    if request.user != pm.owner:
        return Response(status=status.HTTP_403_FORBIDDEN)
    return None


def _has_access(user, pm) -> bool:
    """True if user owns or has been granted shared access to pm."""
    from ..models import ProjectAccess
    if pm.owner == user:
        return True
    return ProjectAccess.objects.filter(
        share_token__project_map=pm, user=user
    ).exists()


def _require_access(request, pm):
    if not _has_access(request.user, pm):
        return Response(status=status.HTTP_403_FORBIDDEN)
    return None
