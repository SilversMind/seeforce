import secrets

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from ..models import ProjectMap, ShareToken, ProjectAccess
from ._permissions import _require_auth, _require_owner


@api_view(["GET", "POST", "DELETE"])
def manage_share(request, project_map_id):
    """Owner: GET returns current token, POST creates one, DELETE revokes."""
    if err := _require_auth(request):
        return err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_owner(request, pm):
        return err

    if request.method == "DELETE":
        pm.share_tokens.all().delete()
        return Response({"revoked": True})

    token_obj = pm.share_tokens.first()

    if request.method == "POST" and not token_obj:
        token_obj = ShareToken.objects.create(
            project_map=pm,
            token=secrets.token_urlsafe(32),
        )

    if not token_obj:
        return Response({"token": None})

    return Response({"token": token_obj.token})


@api_view(["GET"])
def use_share(request, token):
    """Any logged-in user: registers access and returns project metadata."""
    if err := _require_auth(request):
        return err
    try:
        token_obj = ShareToken.objects.select_related("project_map__owner").get(token=token)
    except ShareToken.DoesNotExist:
        return Response({"error": "Invalid or revoked share link."}, status=status.HTTP_404_NOT_FOUND)

    pm = token_obj.project_map

    if pm.owner != request.user:
        ProjectAccess.objects.get_or_create(share_token=token_obj, user=request.user)

    return Response({
        "id": pm.id,
        "name": pm.name,
        "project_id": pm.project_id,
        "owner_username": pm.owner.username if pm.owner else None,
        "is_owner": pm.owner == request.user,
    })


@api_view(["GET"])
def shared_projects(request):
    """Return projects shared with the current user (via ProjectAccess)."""
    if err := _require_auth(request):
        return err
    accesses = (
        ProjectAccess.objects
        .filter(user=request.user)
        .select_related("share_token__project_map__owner")
        .order_by("-added_at")
    )
    return Response([
        {
            "id": a.share_token.project_map.id,
            "name": a.share_token.project_map.name,
            "project_id": a.share_token.project_map.project_id,
            "updated_at": a.share_token.project_map.updated_at,
            "owner_username": a.share_token.project_map.owner.username if a.share_token.project_map.owner else None,
            "shared": True,
        }
        for a in accesses
    ])
