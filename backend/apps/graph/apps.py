from django.apps import AppConfig


class GraphConfig(AppConfig):
    """
    @c2:container
    name: Graph API
    system: C4 Tool
    technology: Python/Django
    description: Stores and serves workspace.json to the frontend
    uses:
      - c4parser
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.graph"
    label = "graph"
