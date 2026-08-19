"""
@c3:component
name: Edit API
container: Backend
description: Handles all user-driven mutations on a project map — node description overlays, edge label overlays, and per-project lexicon entries (create, update, delete).
uses:
- Database: "reads and writes NodeOverlay, EdgeOverlay, and LexiconEntry rows"
"""

import json
import time

from django.db import close_old_connections
from django.http import StreamingHttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from ..models import ProjectMap, NodeOverlay, EdgeOverlay
from ..serializers import (
    ProjectMapSerializer,
    ProjectMapUploadSerializer,
    NodeOverlaySerializer,
    EdgeOverlaySerializer,
)
from ..transformers import to_react_flow
from ._permissions import IsAuthenticatedOrReturn401, IsOwner, _require_auth, _require_owner, _require_access


class ProjectMapViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticatedOrReturn401, IsOwner]
    lookup_value_regex = r"\d+"
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def handle_exception(self, exc):
        from rest_framework.exceptions import NotAuthenticated
        if isinstance(exc, NotAuthenticated):
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)

    def get_queryset(self):
        if self.action == "list":
            return ProjectMap.objects.filter(owner=self.request.user).order_by("-updated_at")
        return ProjectMap.objects.all()

    def list(self, request, *args, **kwargs):
        pms = self.get_queryset()
        return Response([
            {"id": pm.id, "name": pm.name, "project_id": pm.project_id, "updated_at": pm.updated_at}
            for pm in pms
        ])

    def create(self, request, *args, **kwargs):
        ser = ProjectMapUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        pm = ProjectMap.objects.create(
            name=ser.validated_data["name"],
            source_json=ser.validated_data["workspace"],
            owner=request.user,
        )
        return Response(
            {"id": pm.id, "name": pm.name, "created_at": pm.created_at},
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        pm = self.get_object()
        return Response(ProjectMapSerializer(pm).data)

    def partial_update(self, request, *args, **kwargs):
        pm = self.get_object()
        name = request.data.get("name", "").strip()
        if not name:
            return Response({"name": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        pm.name = name
        pm.save(update_fields=["name", "updated_at"])
        return Response({"id": pm.id, "name": pm.name, "updated_at": pm.updated_at})

    def destroy(self, request, *args, **kwargs):
        pm = self.get_object()
        pm.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def latest_project_map(request):
    if err := _require_auth(request):
        return err
    pm = ProjectMap.objects.filter(owner=request.user).order_by("-updated_at").first()
    if not pm:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response({"id": pm.id, "name": pm.name, "project_id": pm.project_id})


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
    if err := _require_auth(request):
        return err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_owner(request, pm):
        return err

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
    obj.tags = d["tags"]
    obj.save()
    return Response({"ok": True})


@api_view(["POST"])
def upsert_edge_overlay(request, project_map_id):
    if err := _require_auth(request):
        return err
    try:
        pm = ProjectMap.objects.get(id=project_map_id)
    except ProjectMap.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    if err := _require_owner(request, pm):
        return err

    ser = EdgeOverlaySerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    d = ser.validated_data
    obj, _ = EdgeOverlay.objects.get_or_create(project_map=pm, edge_id=d["edge_id"])
    obj.label = d["label"]
    obj.save()
    return Response({"ok": True})


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


def scan_events(request):
    """SSE endpoint — polls DB every 2s, emits scan_complete when updated_at changes."""
    if not request.user.is_authenticated:
        from django.http import HttpResponse
        return HttpResponse(status=401)

    user = request.user  # capture before generator runs to avoid request teardown issues

    def event_stream():
        yield "data: " + json.dumps({"type": "connected"}) + "\n\n"
        last_updated = (
            ProjectMap.objects.filter(owner=user)
            .order_by("-updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )
        while True:
            time.sleep(2)
            close_old_connections()  # force fresh DB read — SQLite caches stale reads otherwise
            latest = (
                ProjectMap.objects.filter(owner=user)
                .order_by("-updated_at")
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
