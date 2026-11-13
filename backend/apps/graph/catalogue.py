"""
@c3:component
name: Feature Catalogue API
container: Backend
technology: Python
description: Shapes the stored feature catalogue for the project payload — drops the review commit down to a boolean so the SHA never leaves the backend, and turns a project with no catalogue into an empty one rather than an error, because having none is a normal state. Carries no drift verdict of any kind, since none is stored and a stale badge would be worse than none at all.
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
