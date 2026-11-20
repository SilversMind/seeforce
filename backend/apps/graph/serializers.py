from rest_framework import serializers

from .models import ProjectMap


class ProjectMapSerializer(serializers.ModelSerializer):
    features = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMap
        fields = ["id", "project_id", "name", "source_json", "created_at", "updated_at", "github_repo", "github_branch", "last_synced_at", "features"]
        read_only_fields = ["id", "created_at", "updated_at", "last_synced_at"]

    def get_features(self, obj) -> dict:
        """Serve the catalogue with reviewed_at collapsed to a boolean and no drift information (FR-024b)."""
        return public_catalogue(obj.features_json)


def public_catalogue(features_json) -> dict:
    """Shape a stored catalogue for the project payload; no catalogue is an empty one, never an error."""
    categories = (features_json or {}).get("categories") or []
    return {
        "categories": [
            {
                "name": category.get("name", ""),
                "features": [
                    {
                        "id": feature.get("id"),
                        "name": feature.get("name"),
                        "intent": feature.get("intent"),
                        "kind": feature.get("kind"),
                        "components": feature.get("components") or [],
                        "reviewed": bool(feature.get("reviewed_at")),
                    }
                    for feature in category.get("features") or []
                ],
            }
            for category in categories
        ]
    }


class ProjectMapUploadSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    workspace = serializers.JSONField()
    features = serializers.JSONField(required=False, allow_null=True)

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
