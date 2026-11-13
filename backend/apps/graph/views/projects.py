"""
@c3:component
name: Project Lifecycle
container: Backend
technology: Python / Django REST Framework
description: Owns a project as an object — lists the ones a user has, creates one from an uploaded workspace snapshot, renames it, and deletes it. Holds no opinion on what the snapshot contains; the model arrives whole from a scan or an import and is replaced whole, never patched here.
short_desc: Lists, creates, renames and deletes projects
uses:
- Database/Database: "reads and writes the ProjectMap rows a user owns"
- Feature Catalogue API: "shapes the stored catalogue into the form the project payload carries"
"""

from rest_framework import status, viewsets
from rest_framework.response import Response

from ..models import ProjectMap, sync_lexicon_entries
from ..serializers import ProjectMapSerializer, ProjectMapUploadSerializer
from ._permissions import IsAuthenticatedOrReturn401, IsOwner


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
            {"id": pm.id, "name": pm.name, "project_id": pm.project_id,
             "updated_at": pm.updated_at, "last_synced_at": pm.last_synced_at}
            for pm in pms
        ])

    def create(self, request, *args, **kwargs):
        ser = ProjectMapUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        pm = ProjectMap.objects.create(
            name=ser.validated_data["name"],
            source_json=ser.validated_data["workspace"],
            features_json=ser.validated_data.get("features"),
            owner=request.user,
        )
        sync_lexicon_entries(pm, ser.validated_data["workspace"])
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
