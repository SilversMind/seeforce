"""
@c3:component
name: Feature Catalogue API
container: Backend
technology: Python
description: |
  - Shapes the stored feature catalogue for the project payload
  - Reduces the review commit to a boolean, so the SHA stays in the backend
  - Returns an empty catalogue for a project that has none
short_desc: Shapes the stored feature catalogue for the project payload
"""


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
