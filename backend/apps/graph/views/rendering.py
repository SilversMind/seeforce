"""
@c3:component
name: Map Rendering
container: Backend
technology: Python / Django REST Framework
description: The application's main read path — turns a project's stored workspace snapshot plus the overlays a reader has written on top of it into the nodes and edges the canvas draws for one C4 level, and serves the tag list the same view filters on. Reads both the derived model and the authored overlay, and writes neither.
short_desc: Serves the rendered map for a level, and its tag list
uses:
- Database/Database: "reads the ProjectMap snapshot and the overlays applied to it"
- Graph transformer: "converts the requested project's workspace.json into the ReactFlow nodes and edges the canvas draws"
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import NodeOverlay, ProjectMap
from ..transformers import overlay_maps, to_react_flow
from ._permissions import _require_access, _require_auth


@api_view(["GET"])
def project_map_view(request, project_map_id, level):
    if err := _require_auth(request):
        return err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_access(request, pm):
        return err

    system = request.query_params.get("system")
    container = request.query_params.get("container")

    node_overlay, edge_overlay = overlay_maps(pm)

    result = to_react_flow(
        pm.source_json,
        level=level,
        system=system,
        container=container,
        node_overlay=node_overlay,
        edge_overlay=edge_overlay,
    )
    return Response(result)


@api_view(["GET"])
def project_tags(request, project_map_id):
    if err := _require_auth(request):
        return err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_access(request, pm):
        return err

    all_tags: set[str] = set()
    for ov in NodeOverlay.objects.filter(project_map=pm):
        all_tags.update(ov.tags or [])
    return Response({"tags": sorted(all_tags)})
