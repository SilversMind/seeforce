from django.conf import settings
from django.db import models


class ProjectMap(models.Model):
    project_id = models.CharField(max_length=100, null=True, blank=True, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    source_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projects",
    )
    visibility = models.CharField(max_length=16, default="public")
    github_repo = models.CharField(max_length=255, blank=True, default="")
    github_branch = models.CharField(max_length=255, blank=True, default="main")

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
    project_map = models.ForeignKey(ProjectMap, on_delete=models.CASCADE, related_name="node_overlays")
    node_type = models.CharField(max_length=20, choices=NODE_TYPES)
    system_name = models.CharField(max_length=255, blank=True, default="")
    container_name = models.CharField(max_length=255, blank=True, default="")
    node_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("project_map", "node_type", "system_name", "container_name", "node_name")]

    def __str__(self) -> str:
        return f"{self.node_type}:{self.node_name} ({self.project_map})"


class EdgeOverlay(models.Model):
    project_map = models.ForeignKey(ProjectMap, on_delete=models.CASCADE, related_name="edge_overlays")
    edge_id = models.CharField(max_length=500)
    label = models.CharField(max_length=500, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("project_map", "edge_id")]

    def __str__(self) -> str:
        return f"edge:{self.edge_id} ({self.project_map})"


class ShareToken(models.Model):
    project_map = models.ForeignKey(ProjectMap, on_delete=models.CASCADE, related_name="share_tokens")
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.token:
            import secrets
            self.token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"share:{self.token[:8]}… ({self.project_map})"


class ProjectAccess(models.Model):
    share_token = models.ForeignKey(ShareToken, on_delete=models.CASCADE, related_name="accesses")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_accesses")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("share_token", "user")]

    def __str__(self) -> str:
        return f"{self.user} → {self.share_token.project_map}"


class LexiconEntry(models.Model):
    project_map = models.ForeignKey(ProjectMap, on_delete=models.CASCADE, related_name="lexicon_entries")
    term = models.CharField(max_length=255)
    definition = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("project_map", "term")]

    def __str__(self) -> str:
        return f"{self.term} ({self.project_map})"


def sync_lexicon_entries(project_map: "ProjectMap", workspace: dict) -> None:
    """Upsert LexiconEntry rows from a scanned workspace's "lexicon" list
    (populated by @lexicon annotations). Never deletes — entries added
    manually through the UI, or terms dropped from the source, are left
    alone rather than silently disappearing on the next scan/sync."""
    for entry in workspace.get("lexicon", []) or []:
        term = entry.get("term")
        definition = entry.get("definition")
        if not term or not definition:
            continue
        # Case-insensitive: don't create a second entry for "OSV" if "osv"
        # already exists (e.g. one added manually, one from a re-scan).
        row = project_map.lexicon_entries.filter(term__iexact=term).first()
        if row is None:
            row = LexiconEntry(project_map=project_map, term=term)
        row.definition = definition
        row.save()
