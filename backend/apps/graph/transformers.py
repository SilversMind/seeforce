def _node(id: str, node_type: str, label: str, technology: str = "", description: str = "") -> dict:
    return {
        "id": id,
        "type": node_type,
        "position": {"x": 0, "y": 0},
        "data": {"label": label, "technology": technology, "description": description},
    }


def _edge(rel: dict, source_id: str) -> dict:
    return {
        "id": rel["id"],
        "source": source_id,
        "target": rel["destinationId"],
        "label": rel.get("description", ""),
        "type": "relation",
    }


def _is_external(element: dict) -> bool:
    return "External" in element.get("tags", "")


def to_react_flow(
    workspace_json: dict,
    level: str,
    system: str | None,
    container: str | None,
) -> dict:
    model = workspace_json.get("model", {})

    match level:
        case "C1":
            return _c1_view(model)
        case "C2":
            return _c2_view(model, system)
        case "C3":
            return _c3_view(model, container)
        case _:
            return {"nodes": [], "edges": []}


def _c1_view(model: dict) -> dict:
    nodes = []
    edges = []

    for person in model.get("people", []):
        nodes.append(_node(person["id"], "person", person["name"], description=person.get("description", "")))
        for rel in person.get("relationships", []):
            edges.append(_edge(rel, person["id"]))

    for system in model.get("softwareSystems", []):
        node_type = "external" if _is_external(system) else "system"
        nodes.append(_node(system["id"], node_type, system["name"], description=system.get("description", "")))
        for rel in system.get("relationships", []):
            edges.append(_edge(rel, system["id"]))

    return {"nodes": nodes, "edges": edges}


def _c2_view(model: dict, system_id: str | None) -> dict:
    if not system_id:
        return {"nodes": [], "edges": []}

    target = next(
        (s for s in model.get("softwareSystems", []) if s["id"] == system_id),
        None,
    )
    if not target:
        return {"nodes": [], "edges": []}

    nodes = []
    edges = []

    for container in target.get("containers", []):
        nodes.append(_node(
            container["id"], "container", container["name"],
            technology=container.get("technology", ""),
            description=container.get("description", ""),
        ))
        for rel in container.get("relationships", []):
            edges.append(_edge(rel, container["id"]))

    return {"nodes": nodes, "edges": edges}


def _c3_view(model: dict, container_id: str | None) -> dict:
    if not container_id:
        return {"nodes": [], "edges": []}

    for system in model.get("softwareSystems", []):
        for container in system.get("containers", []):
            if container["id"] != container_id:
                continue
            nodes = []
            edges = []
            for comp in container.get("components", []):
                nodes.append(_node(
                    comp["id"], "component", comp["name"],
                    technology=comp.get("technology", ""),
                    description=comp.get("description", ""),
                ))
                for rel in comp.get("relationships", []):
                    edges.append(_edge(rel, comp["id"]))
            return {"nodes": nodes, "edges": edges}

    return {"nodes": [], "edges": []}
