"""
@c3:component
name: Workspace Navigation Helpers
container: MCP Server
technology: Python
description: Pure lookup helpers over the fetched workspace dict — enumerating systems, containers, components, and external systems, and rendering a relationship as a human-readable line for tool output.
"""
"""Helpers for navigating a SeeForce workspace dict."""


def all_systems(ws: dict) -> list[dict]:
    return ws.get("model", {}).get("softwareSystems", [])


def all_containers(ws: dict) -> list[dict]:
    result = []
    for sys in all_systems(ws):
        for cont in sys.get("containers", []):
            result.append({**cont, "_system": sys["name"]})
    return result


def all_components(ws: dict) -> list[dict]:
    result = []
    for sys in all_systems(ws):
        for cont in sys.get("containers", []):
            for comp in cont.get("components", []):
                result.append({**comp, "_container": cont["name"], "_system": sys["name"]})
    return result


def external_systems(ws: dict) -> list[dict]:
    return [s for s in all_systems(ws) if "External" in s.get("tags", "")]


def id_to_name(dest_id: str, ws: dict) -> str:
    for el in all_systems(ws) + all_containers(ws) + all_components(ws):
        if el.get("id") == dest_id:
            return el.get("name", dest_id)
    return dest_id


def format_rel(rel: dict, ws: dict) -> str:
    name = id_to_name(rel.get("destinationId", ""), ws)
    desc = rel.get("description", "")
    tech = rel.get("technology", "")
    tech_str = f" [{tech}]" if tech else ""
    return f"→ {name}{tech_str}: {desc}" if desc else f"→ {name}{tech_str}"
