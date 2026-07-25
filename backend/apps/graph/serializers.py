from rest_framework import serializers
from .models import Workspace


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ["id", "name", "source_json", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class WorkspaceUploadSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    workspace = serializers.JSONField()

    def validate_workspace(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("workspace must be a JSON object")
        return value


class NodeOverlaySerializer(serializers.Serializer):
    node_type = serializers.ChoiceField(choices=["system", "container", "component", "person", "external"])
    system_name = serializers.CharField(max_length=255, default="", allow_blank=True)
    container_name = serializers.CharField(max_length=255, default="", allow_blank=True)
    node_name = serializers.CharField(max_length=255)
    display_name = serializers.CharField(max_length=255, default="", allow_blank=True)
    description = serializers.CharField(default="", allow_blank=True)


class EdgeOverlaySerializer(serializers.Serializer):
    edge_id = serializers.CharField(max_length=500)
    label = serializers.CharField(max_length=500, default="", allow_blank=True)
