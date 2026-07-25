from django.db import models


class Workspace(models.Model):
    name = models.CharField(max_length=255)
    source_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.name


class NodeOverlay(models.Model):
    NODE_TYPES = [
        ("system", "System"),
        ("container", "Container"),
        ("component", "Component"),
        ("person", "Person"),
        ("external", "External"),
    ]
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="node_overlays")
    node_type = models.CharField(max_length=20, choices=NODE_TYPES)
    system_name = models.CharField(max_length=255, blank=True, default="")
    container_name = models.CharField(max_length=255, blank=True, default="")
    node_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("workspace", "node_type", "system_name", "container_name", "node_name")]

    def __str__(self) -> str:
        return f"{self.node_type}:{self.node_name} ({self.workspace})"


class EdgeOverlay(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name="edge_overlays")
    edge_id = models.CharField(max_length=500)
    label = models.CharField(max_length=500, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("workspace", "edge_id")]

    def __str__(self) -> str:
        return f"edge:{self.edge_id} ({self.workspace})"
