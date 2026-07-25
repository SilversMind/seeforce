from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Workspace, NodeOverlay, EdgeOverlay
from .serializers import (
    WorkspaceSerializer,
    WorkspaceUploadSerializer,
    NodeOverlaySerializer,
    EdgeOverlaySerializer,
)
from .transformers import to_react_flow


@api_view(["POST"])
def upload_workspace(request):
    ser = WorkspaceUploadSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
    ws = Workspace.objects.create(
        name=ser.validated_data["name"],
        source_json=ser.validated_data["workspace"],
    )
    return Response(
        {"id": ws.id, "name": ws.name, "created_at": ws.created_at},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def fetch_workspace(request, workspace_id):
    try:
        ws = Workspace.objects.get(id=workspace_id)
    except Workspace.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)
    return Response(WorkspaceSerializer(ws).data)


@api_view(["GET"])
def workspace_view(request, workspace_id, level):
    try:
        ws = Workspace.objects.get(id=workspace_id)
    except Workspace.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    system = request.query_params.get("system")
    container = request.query_params.get("container")

    node_overlay = {
        (ov.node_type, ov.system_name, ov.container_name, ov.node_name): {
            "display_name": ov.display_name,
            "description": ov.description,
        }
        for ov in NodeOverlay.objects.filter(workspace=ws)
    }
    edge_overlay = {
        ov.edge_id: {"label": ov.label}
        for ov in EdgeOverlay.objects.filter(workspace=ws)
    }

    result = to_react_flow(
        ws.source_json,
        level=level,
        system=system,
        container=container,
        node_overlay=node_overlay,
        edge_overlay=edge_overlay,
    )
    return Response(result)


@api_view(["POST"])
def upsert_node_overlay(request, workspace_id):
    try:
        ws = Workspace.objects.get(id=workspace_id)
    except Workspace.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    ser = NodeOverlaySerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    d = ser.validated_data
    obj, _ = NodeOverlay.objects.get_or_create(
        workspace=ws,
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
def upsert_edge_overlay(request, workspace_id):
    try:
        ws = Workspace.objects.get(id=workspace_id)
    except Workspace.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    ser = EdgeOverlaySerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    d = ser.validated_data
    obj, _ = EdgeOverlay.objects.get_or_create(workspace=ws, edge_id=d["edge_id"])
    obj.label = d["label"]
    obj.save()

    return Response({"ok": True})
