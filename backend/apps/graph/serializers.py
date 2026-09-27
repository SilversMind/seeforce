from rest_framework import serializers

from .models import ProjectMap


class ProjectMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectMap
        fields = ["id", "project_id", "name", "source_json", "created_at", "updated_at", "github_repo", "github_branch"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProjectMapUploadSerializer(serializers.Serializer):
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
    tags = serializers.ListField(child=serializers.CharField(max_length=64), default=list)


class EdgeOverlaySerializer(serializers.Serializer):
    edge_id = serializers.CharField(max_length=500)
    label = serializers.CharField(max_length=500, default="", allow_blank=True)


class LexiconEntrySerializer(serializers.Serializer):
    term = serializers.CharField(max_length=255)
    definition = serializers.CharField()
