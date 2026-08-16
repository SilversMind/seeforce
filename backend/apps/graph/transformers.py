"""
@c3:component
name: Graph transformer
container: Backend
description: Convert architecture scan data into graph data usable by ReactFlow
uses:
  - Architecture Scanner: "Calls scan() to extract C4 elements from annotated source files"

"""

_GRID_COLS = 4
_GRID_X = 300
_GRID_Y = 180

# overlay_key tuple: (node_type, system_name, container_name, node_name)
OverlayKey = tuple[str, str, str, str]


def _node(
    id: str,
    node_type: str,
    label: str,
    technology: str = "",
    description: str = "",
    *,
    overlay_key: OverlayKey | None = None,
    node_overlay: dict[OverlayKey, dict] | None = None,
) -> dict:
    ov = node_overlay.get(overlay_key) if (node_overlay and overlay_key) else None
    ctx = overlay_key or (node_type, "", "", label)
    return {
        "id": id,
        "type": node_type,
        "position": {"x": 0, "y": 0},
        "data": {
            "label": label,
            "technology": technology,
            "description": description,
            "overlay_label": ov.get("display_name", "") if ov else "",
            "overlay_description": ov.get("description", "") if ov else "",
            "has_overlay": bool(ov and (ov.get("display_name") or ov.get("description"))),
            "overlay_key": {
                "node_type": ctx[0],
                "system_name": ctx[1],
                "container_name": ctx[2],
                "node_name": ctx[3],
            },
        },
    }


def _layout(nodes: list[dict]) -> list[dict]:
    # Deterministic grid: fill rows left-to-right, wrap every _GRID_COLS nodes.
    for index, node in enumerate(nodes):
        node["position"] = {
            "x": (index % _GRID_COLS) * _GRID_X,
            "y": (index // _GRID_COLS) * _GRID_Y,
        }
    return nodes


def _edge(
    rel: dict,
    source_id: str,
    edge_overlay: dict[str, dict] | None = None,
) -> dict | None:
    if rel["destinationId"] == source_id:
        return None
    eid = rel["id"]
    ov = edge_overlay.get(eid) if edge_overlay else None
    return {
        "id": eid,
        "source": source_id,
        "target": rel["destinationId"],
        "label": rel.get("description", ""),
        "type": "relation",
        "data": {
            "overlay_label": ov.get("label", "") if ov else "",
            "has_overlay": bool(ov and ov.get("label")),
            "technology": rel.get("technology", ""),
        },
    }


def _merge_parallel_edges(edges: list[dict]) -> list[dict]:
    """Merge edges sharing the same source+target into one, combining labels and technologies."""
    from copy import deepcopy
    seen: dict[tuple[str, str], dict] = {}
    result: list[dict] = []
    for edge in edges:
        key = (edge["source"], edge["target"])
        if key not in seen:
            seen[key] = deepcopy(edge)
            result.append(seen[key])
        else:
            existing = seen[key]
            new_label = edge.get("label", "")
            existing_label = existing.get("label", "")
            if new_label and new_label not in existing_label:
                existing["label"] = f"{existing_label}, {new_label}" if existing_label else new_label
            new_tech = edge.get("data", {}).get("technology", "")
            existing_tech = existing.get("data", {}).get("technology", "")
            if new_tech and new_tech not in existing_tech:
                existing["data"]["technology"] = f"{existing_tech}, {new_tech}" if existing_tech else new_tech
    return result


def _is_external(element: dict) -> bool:
    return "External" in element.get("tags", "")


def _element_index(model: dict) -> dict[str, dict]:
    """Map every element id in the model to its name and kind."""
    index: dict[str, dict] = {}
    for person in model.get("people", []):
        index[person["id"]] = {"name": person["name"], "kind": "person"}
    for system in model.get("softwareSystems", []):
        kind = "external" if _is_external(system) else "system"
        index[system["id"]] = {"name": system["name"], "kind": kind}
        for container in system.get("containers", []):
            index[container["id"]] = {"name": container["name"], "kind": "container"}
            for comp in container.get("components", []):
                index[comp["id"]] = {"name": comp["name"], "kind": "component"}
    return index


def _add_placeholders(
    nodes: list[dict],
    edges: list[dict],
    model: dict,
    node_overlay: dict[OverlayKey, dict] | None = None,
) -> None:
    """Emit placeholder nodes for edge endpoints outside the current node set."""
    known = {n["id"] for n in nodes}
    index = _element_index(model)
    for edge in edges:
        for endpoint in (edge["source"], edge["target"]):
            if endpoint in known:
                continue
            info = index.get(endpoint)
            kind = info["kind"] if info else "external"
            name = info["name"] if info else endpoint
            okey: OverlayKey = (kind, "", "", name)
            nodes.append(_node(endpoint, "external", name, overlay_key=okey, node_overlay=node_overlay))
            known.add(endpoint)


def to_react_flow(
    workspace_json: dict,
    level: str,
    system: str | None,
    container: str | None,
    node_overlay: dict[OverlayKey, dict] | None = None,
    edge_overlay: dict[str, dict] | None = None,
) -> dict:
    model = workspace_json.get("model", {})

    match level:
        case "C1":
            return _c1_view(model, node_overlay, edge_overlay)
        case "C2":
            return _c2_view(model, system, node_overlay, edge_overlay)
        case "C3":
            return _c3_view(model, container, node_overlay, edge_overlay)
        case _:
            return {"nodes": [], "edges": []}


def _c1_view(
    model: dict,
    node_overlay: dict[OverlayKey, dict] | None,
    edge_overlay: dict[str, dict] | None,
) -> dict:
    nodes = []
    edges = []

    for person in model.get("people", []):
        okey: OverlayKey = ("person", "", "", person["name"])
        nodes.append(
            _node(
                person["id"],
                "person",
                person["name"],
                description=person.get("description", ""),
                overlay_key=okey,
                node_overlay=node_overlay,
            )
        )
        for rel in person.get("relationships", []):
            if (e := _edge(rel, person["id"], edge_overlay)) is not None:
                edges.append(e)

    for system in model.get("softwareSystems", []):
        node_type = "external" if _is_external(system) else "system"
        okey = (node_type, "", "", system["name"])
        nodes.append(
            _node(
                system["id"],
                node_type,
                system["name"],
                description=system.get("description", ""),
                overlay_key=okey,
                node_overlay=node_overlay,
            )
        )
        for rel in system.get("relationships", []):
            if (e := _edge(rel, system["id"], edge_overlay)) is not None:
                edges.append(e)

    return {"nodes": _layout(nodes), "edges": _merge_parallel_edges(edges)}


def _c2_view(
    model: dict,
    system_id: str | None,
    node_overlay: dict[OverlayKey, dict] | None,
    edge_overlay: dict[str, dict] | None,
) -> dict:
    if not system_id:
        return {"nodes": [], "edges": []}

    target = next(
        (s for s in model.get("softwareSystems", []) if s["id"] == system_id),
        None,
    )
    if not target:
        return {"nodes": [], "edges": []}

    system_name = target["name"]
    nodes = []
    edges = []

    for container in target.get("containers", []):
        okey: OverlayKey = ("container", system_name, "", container["name"])
        nodes.append(
            _node(
                container["id"],
                "container",
                container["name"],
                technology=container.get("technology", ""),
                description=container.get("description", ""),
                overlay_key=okey,
                node_overlay=node_overlay,
            )
        )
        for rel in container.get("relationships", []):
            if (e := _edge(rel, container["id"], edge_overlay)) is not None:
                edges.append(e)

    _add_placeholders(nodes, edges, model, node_overlay)
    return {"nodes": _layout(nodes), "edges": _merge_parallel_edges(edges)}


def _c3_view(
    model: dict,
    container_id: str | None,
    node_overlay: dict[OverlayKey, dict] | None,
    edge_overlay: dict[str, dict] | None,
) -> dict:
    if not container_id:
        return {"nodes": [], "edges": []}

    for system in model.get("softwareSystems", []):
        for container in system.get("containers", []):
            if container["id"] != container_id:
                continue
            system_name = system["name"]
            container_name = container["name"]
            nodes = []
            edges = []
            for comp in container.get("components", []):
                okey: OverlayKey = ("component", system_name, container_name, comp["name"])
                nodes.append(
                    _node(
                        comp["id"],
                        "component",
                        comp["name"],
                        technology=comp.get("technology", ""),
                        description=comp.get("description", ""),
                        overlay_key=okey,
                        node_overlay=node_overlay,
                    )
                )
                for rel in comp.get("relationships", []):
                    if (e := _edge(rel, comp["id"], edge_overlay)) is not None:
                        edges.append(e)
            _add_placeholders(nodes, edges, model, node_overlay)
            return {"nodes": _layout(nodes), "edges": _merge_parallel_edges(edges)}

    return {"nodes": [], "edges": []}
