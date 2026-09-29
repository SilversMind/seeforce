import secrets

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..models import ProjectAccess, ProjectMap, ShareToken
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
@permission_classes([AllowAny])  # share links are public by design
def use_share(request, token):
    """Public: returns project metadata. Registers access if user is authenticated."""
    try:
        token_obj = ShareToken.objects.select_related("project_map__owner").get(token=token)
    except ShareToken.DoesNotExist:
        return Response({"error": "Invalid or revoked share link."}, status=status.HTTP_404_NOT_FOUND)

    pm = token_obj.project_map

    if request.user.is_authenticated and pm.owner != request.user:
        ProjectAccess.objects.get_or_create(share_token=token_obj, user=request.user)

    return Response({
        "id": pm.id,
        "name": pm.name,
        "project_id": pm.project_id,
        "owner_username": pm.owner.username if pm.owner else None,
        "is_owner": request.user.is_authenticated and pm.owner == request.user,
    })


@api_view(["GET"])
@permission_classes([AllowAny])  # share links are public by design
def share_view(request, token, level):
    """Public: returns React Flow graph data for a shared project."""
    try:
        token_obj = ShareToken.objects.select_related("project_map").get(token=token)
    except ShareToken.DoesNotExist:
        return Response({"error": "Invalid or revoked share link."}, status=status.HTTP_404_NOT_FOUND)

    from ..models import EdgeOverlay, NodeOverlay
    from ..transformers import to_react_flow

    pm = token_obj.project_map
    system = request.query_params.get("system")
    container = request.query_params.get("container")

    node_overlay = {
        (ov.node_type, ov.system_name, ov.container_name, ov.node_name): {
            "display_name": ov.display_name,
            "description": ov.description,
            "tags": ov.tags,
        }
        for ov in NodeOverlay.objects.filter(project_map=pm)
    }
    edge_overlay = {
        ov.edge_id: {"label": ov.label}
        for ov in EdgeOverlay.objects.filter(project_map=pm)
    }

    result = to_react_flow(pm.source_json, level=level, system=system, container=container,
                           node_overlay=node_overlay, edge_overlay=edge_overlay)
    return Response(result)


def _project_for_token(token: str):
    """Resolve a share token to its project, or None when revoked or unknown."""
    try:
        return ShareToken.objects.select_related("project_map").get(token=token).project_map
    except ShareToken.DoesNotExist:
        return None


@api_view(["GET"])
@permission_classes([AllowAny])  # share links are public by design
def share_lexicon(request, token):
    """Public: the shared project's glossary, so terms stay defined for a visitor."""
    pm = _project_for_token(token)
    if pm is None:
        return Response({"error": "Invalid or revoked share link."}, status=status.HTTP_404_NOT_FOUND)

    from ..models import LexiconEntry
    entries = LexiconEntry.objects.filter(project_map=pm).order_by("term")
    return Response([{"term": e.term, "definition": e.definition} for e in entries])


@api_view(["GET"])
@permission_classes([AllowAny])  # share links are public by design
def share_tags(request, token):
    """Public: the tags used across the shared project's node overlays."""
    pm = _project_for_token(token)
    if pm is None:
        return Response({"error": "Invalid or revoked share link."}, status=status.HTTP_404_NOT_FOUND)

    from ..models import NodeOverlay
    all_tags: set[str] = set()
    for ov in NodeOverlay.objects.filter(project_map=pm):
        all_tags.update(ov.tags or [])
    return Response({"tags": sorted(all_tags)})


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
