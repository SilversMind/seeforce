import json
import time

from django.db import close_old_connections
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import ProjectMap, NodeOverlay, EdgeOverlay
from .serializers import (
    ProjectMapSerializer,
    ProjectMapUploadSerializer,
    NodeOverlaySerializer,
    EdgeOverlaySerializer,
)
from .transformers import to_react_flow


@api_view(["GET"])
def list_project_maps(request):
    pms = ProjectMap.objects.order_by("-updated_at")
    return Response([
        {"id": pm.id, "name": pm.name, "project_id": pm.project_id, "updated_at": pm.updated_at}
        for pm in pms
    ])


@api_view(["POST"])
def upload_project_map(request):
    ser = ProjectMapUploadSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    pm = ProjectMap.objects.create(
        name=ser.validated_data["name"],
        source_json=ser.validated_data["workspace"],
    )
    return Response(
        {"id": pm.id, "name": pm.name, "created_at": pm.created_at},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def fetch_project_map(request, project_map_id):
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(ProjectMapSerializer(pm).data)


@api_view(["GET"])
def latest_project_map(request):
    pm = ProjectMap.objects.order_by("-updated_at").first()
    if not pm:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response({"id": pm.id, "name": pm.name, "project_id": pm.project_id})


@api_view(["GET"])
def project_map_view(request, project_map_id, level):
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    system = request.query_params.get("system")
    container = request.query_params.get("container")

    node_overlay = {
        (ov.node_type, ov.system_name, ov.container_name, ov.node_name): {
            "display_name": ov.display_name,
            "description": ov.description,
        }
        for ov in NodeOverlay.objects.filter(project_map=pm)
    }
    edge_overlay = {
        ov.edge_id: {"label": ov.label}
        for ov in EdgeOverlay.objects.filter(project_map=pm)
    }

    result = to_react_flow(
        pm.source_json,
        level=level,
        system=system,
        container=container,
        node_overlay=node_overlay,
        edge_overlay=edge_overlay,
    )
    return Response(result)


@api_view(["POST"])
def upsert_node_overlay(request, project_map_id):
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    ser = NodeOverlaySerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    d = ser.validated_data
    obj, _ = NodeOverlay.objects.get_or_create(
        project_map=pm,
        node_type=d["node_type"],
        system_name=d["system_name"],
        container_name=d["container_name"],
        node_name=d["node_name"],
    )
    obj.display_name = d["display_name"]
    obj.description = d["description"]
    obj.save()

    return Response({"ok": True})


@api_view(["POST"])
def upsert_edge_overlay(request, project_map_id):
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    ser = EdgeOverlaySerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    d = ser.validated_data
    obj, _ = EdgeOverlay.objects.get_or_create(project_map=pm, edge_id=d["edge_id"])
    obj.label = d["label"]
    obj.save()

    return Response({"ok": True})


def scan_events(request):
    """SSE endpoint — polls DB every 2s, emits scan_complete when updated_at changes."""
    def event_stream():
        yield "data: " + json.dumps({"type": "connected"}) + "\n\n"
        last_updated = (
            ProjectMap.objects.order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )
        while True:
            time.sleep(2)
            close_old_connections()  # force fresh DB read — SQLite caches stale reads otherwise
            latest = (
                ProjectMap.objects.order_by("-updated_at")
                .values("id", "updated_at")
                .first()
            )
            if latest and latest["updated_at"] != last_updated:
                last_updated = latest["updated_at"]
                yield "data: " + json.dumps({"type": "scan_complete", "id": latest["id"]}) + "\n\n"

    response = StreamingHttpResponse(
        streaming_content=event_stream(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response
