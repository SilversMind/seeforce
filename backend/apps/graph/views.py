from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Workspace
from .serializers import WorkspaceSerializer, WorkspaceUploadSerializer
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

    result = to_react_flow(ws.source_json, level=level, system=system, container=container)
    return Response(result)
