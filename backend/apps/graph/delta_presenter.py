"""
@c3:component
name: Delta Presenter
container: Backend
technology: Python
description: Decorates an already-rendered C1/C2/C3 view with the state an architecture comparison gives each element and relation — added, removed, modified or unchanged — rolling a descendant's change up through containment so a component change is visible on its container and its system, injecting the elements a merge request removed as ghost nodes so they keep a position, and summarising every change in the comparison as one list. Pure computation over two workspace dicts and a Delta — no HTTP call, no database read, nothing written, and no risk or merge verdict anywhere in its output.
short_desc: Decorates a rendered view with per-element comparison state
uses:
- Graph transformer: "renders the head workspace into the ReactFlow view this module then decorates, and reuses its node builder for ghost nodes"
- Delta Reporter: "reads the Delta dataclasses — added, removed, changed elements and relations — that this module projects onto the view"
"""
from c4parser.delta import Delta, Element, FieldChange
from c4parser.delta import _render_field as _render_delta_field

from .transformers import _element_index, _node, to_react_flow

_LEVEL_BY_KIND = {"person": "C1", "system": "C1", "container": "C2", "component": "C3"}
# Ancestor kinds, immediate parent first, matching the ancestor paths element_paths derives.
_ANCESTOR_KINDS = {"component": ("container", "system"), "container": ("system",)}
_UNCHANGED = {
    "state": "unchanged", "self_changed": False, "contains_changes": False,
    "fields": [], "possible_rename_of": None, "ghost": False, "declared_parent": None,
}


def element_paths(model: dict) -> dict[str, dict]:
    """Map every element id to the kind, path and ancestor paths that c4parser.delta keys on."""
    out: dict[str, dict] = {}
    for eid, info in _element_index(model).items():
        # NOTE: the delta calls a tagged external system a "system", so the view's node type and the comparison's kind differ here.
        kind = "system" if info["kind"] == "external" else info["kind"]
        if kind == "container":
            path, ancestors = f"{info['name']} ({info['system_name']})", (info["system_name"],)
        elif kind == "component":
            parent = f"{info['container_name']} ({info['system_name']})"
            path, ancestors = f"{info['name']} ({info['container_name']})", (parent, info["system_name"])
        else:
            path, ancestors = info["name"], ()
        out[eid] = {
            "kind": kind, "path": path, "ancestors": ancestors,
            "node_type": info["kind"], "name": info["name"],
        }
    return out


def _fields(changes: list[FieldChange]) -> list[dict]:
    return [{"field": c.field, "before": c.before, "after": c.after} for c in changes]


def _possible_renames(delta: Delta) -> dict[str, str]:
    """Cross-link a removal and an addition sharing one file, which ADR 0001's pairing cannot tell apart."""
    out: dict[str, str] = {}
    for key in {(e.kind, e.source_file) for e in (*delta.added, *delta.removed) if e.source_file}:
        gone = [e for e in delta.removed if (e.kind, e.source_file) == key]
        new = [e for e in delta.added if (e.kind, e.source_file) == key]
        # Only an unambiguous one-for-one swap is labelled; more than one of either side proves nothing.
        if len(gone) == 1 and len(new) == 1:
            out[gone[0].path], out[new[0].path] = new[0].path, gone[0].path
    return out


def _own_states(delta: Delta) -> dict[tuple[str, str], dict]:
    """The state each element carries from its own declaration, keyed by (kind, path)."""
    renames = _possible_renames(delta)
    own: dict[tuple[str, str], dict] = {}
    for e in delta.added:
        own[(e.kind, e.path)] = {**_UNCHANGED, "state": "added", "possible_rename_of": renames.get(e.path)}
    for e in delta.removed:
        own[(e.kind, e.path)] = {
            **_UNCHANGED, "state": "removed", "ghost": True,
            "possible_rename_of": renames.get(e.path),
        }
    for c in delta.changed:
        own[(c.kind, c.path)] = {
            **_UNCHANGED, "state": "modified", "self_changed": True, "fields": _fields(c.fields),
        }
    return own


def _by_path(*indexes: dict[str, dict]) -> dict[tuple[str, str], dict]:
    """Reverse the id-keyed indexes into (kind, path) -> info, head before base."""
    out: dict[tuple[str, str], dict] = {}
    for index in indexes:
        for eid, info in index.items():
            out.setdefault((info["kind"], info["path"]), {**info, "id": eid})
    return out


def _endpoint(path: str, by_path: dict[tuple[str, str], dict]) -> dict | None:
    """Find a relation endpoint from its path alone, which carries no kind."""
    # NOTE: a person and a system of one name share a path, so the first kind that matches wins.
    for kind in ("component", "container", "system", "person"):
        if (found := by_path.get((kind, path))) is not None:
            return found
    return None


def _contains(delta: Delta, own: dict[tuple[str, str], dict], by_path: dict[tuple[str, str], dict]) -> set[tuple[str, str]]:
    """Every element enclosing a change, found through containment only — never along a relation."""
    out: set[tuple[str, str]] = set()

    def climb(kind: str, path: str) -> None:
        info = by_path.get((kind, path))
        if info is None:
            return
        for akind, apath in zip(_ANCESTOR_KINDS.get(kind, ()), info["ancestors"]):
            out.add((akind, apath))

    for kind, path in own:
        climb(kind, path)
    for edge in (*delta.edges_added, *delta.edges_removed, *delta.edges_changed):
        for path in (edge.source_path, edge.dest_path):
            if (info := _endpoint(path, by_path)) is not None:
                climb(info["kind"], info["path"])
    return out


def _ghost_node(element: Element, node_type: str, declared_parent: str | None, state: dict) -> dict:
    """Draw an element the merge request removed, keeping its id so a saved position still applies."""
    node = _node(
        element.id, node_type, element.fields.get("name", "") or element.name,
        technology=element.fields.get("technology", ""),
        description=element.fields.get("description", ""),
        short_desc=element.fields.get("short_desc", ""),
        code_ref=element.source_file,
    )
    node["data"]["delta"] = {**state, "declared_parent": declared_parent}
    return node


def _ghost_parent_path(level: str, target: str | None, head_paths: dict, base_paths: dict) -> str | None:
    """The base-side path whose children are the ghosts this level should show."""
    for index in (head_paths, base_paths):
        if target in index:
            return index[target]["path"] if level == "C3" else index[target]["name"]
    return None


def _ghosts(delta: Delta, level: str, target: str | None, head_paths: dict, base_paths: dict,
            own: dict[tuple[str, str], dict], present: set[str]) -> list[dict]:
    kinds = {"C1": ("person", "system"), "C2": ("container",), "C3": ("component",)}[level]
    parent = _ghost_parent_path(level, target, head_paths, base_paths)
    out: list[dict] = []
    for element in delta.removed:
        if element.kind not in kinds or element.id in present:
            continue
        info = base_paths.get(element.id, {})
        ancestors = info.get("ancestors", ())
        if level != "C1" and (not ancestors or ancestors[0] != parent):
            continue
        orphan = ancestors and (_ANCESTOR_KINDS[element.kind][0], ancestors[0]) in own
        out.append(_ghost_node(
            element, info.get("node_type", element.kind),
            ancestors[0] if orphan else None,
            own[(element.kind, element.path)],
        ))
    return out


def _edge_states(delta: Delta) -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    for e in delta.edges_added:
        out[(e.source_path, e.dest_path)] = {"state": "added", "fields": [], "ghost": False}
    for c in delta.edges_changed:
        out[(c.source_path, c.dest_path)] = {
            "state": "modified", "fields": _fields(c.fields), "ghost": False,
        }
    return out


def _ghost_edges(delta: Delta, node_paths: dict[str, str]) -> list[dict]:
    """Draw a relation the merge request removed, between whichever of its endpoints this level shows."""
    ids = {path: nid for nid, path in node_paths.items()}
    out: list[dict] = []
    for edge in delta.edges_removed:
        source, target = ids.get(edge.source_path), ids.get(edge.dest_path)
        if source is None or target is None:
            continue
        out.append({
            "id": f"removed:{source}:{target}", "source": source, "target": target,
            "label": edge.description, "type": "relation",
            "data": {
                "overlay_label": "", "has_overlay": False, "technology": edge.technology,
                "delta": {"state": "removed", "fields": [], "ghost": True},
            },
        })
    return out


def _summarise(state: str, element_fields: list[dict], source_file: str) -> str:
    if state == "modified":
        return "; ".join(
            _render_delta_field(FieldChange(f["field"], f["before"], f["after"])) for f in element_fields
        )
    return f"{state} — {source_file}" if source_file else state


def _changes(delta: Delta, by_path: dict[tuple[str, str], dict]) -> list[dict]:
    """Every change in the comparison, at every level, so nothing has to be hunted on the canvas."""
    out: list[dict] = []
    for state, elements in (("added", delta.added), ("removed", delta.removed)):
        for e in elements:
            out.append({
                "kind": e.kind, "path": e.path, "state": state,
                "level": _LEVEL_BY_KIND[e.kind], "node_id": e.id,
                "summary": _summarise(state, [], e.source_file),
            })
    for c in delta.changed:
        fields = _fields(c.fields)
        out.append({
            "kind": c.kind, "path": c.path, "state": "modified",
            "level": _LEVEL_BY_KIND[c.kind],
            "node_id": by_path.get((c.kind, c.path), {}).get("id"),
            "summary": _summarise("modified", fields, c.source_file),
        })
    for state, edges in (("added", delta.edges_added), ("removed", delta.edges_removed)):
        for e in edges:
            out.append(_edge_change(state, e.source_path, e.dest_path, [], e.description, by_path))
    for c in delta.edges_changed:
        out.append(_edge_change("modified", c.source_path, c.dest_path, _fields(c.fields), "", by_path))
    return out


def _edge_change(state: str, source: str, dest: str, fields: list[dict], description: str,
                 by_path: dict[tuple[str, str], dict]) -> dict:
    endpoint = _endpoint(source, by_path)
    return {
        "kind": "relation", "path": f"{source} → {dest}", "state": state,
        "level": _LEVEL_BY_KIND[endpoint["kind"]] if endpoint else "C1",
        "node_id": endpoint["id"] if endpoint else None,
        "summary": _summarise(state, fields, "") if state == "modified" else (
            f'{state} — "{description}"' if description else state
        ),
    }


def _replace_placeholders(nodes: list[dict], delta: Delta, source_paths: dict, base_paths: dict,
                          own: dict[tuple[str, str], dict]) -> None:
    """Redraw a removed element the head view still shows as a relation placeholder."""
    # NOTE: a relation pointing at it survives in head, so the view invents a bare placeholder node where the real ghost belongs.
    removed = {e.id: e for e in delta.removed if e.id}
    for index, node in enumerate(nodes):
        if node["id"] in source_paths or node["id"] not in base_paths:
            continue
        if (element := removed.get(node["id"])) is None:
            continue
        info = base_paths[node["id"]]
        nodes[index] = _ghost_node(
            element, info["node_type"], None, own[(info["kind"], info["path"])]
        )


def decorate(
    base_ws: dict,
    head_ws: dict,
    delta: Delta,
    level: str,
    system: str | None = None,
    container: str | None = None,
    node_overlay: dict | None = None,
    edge_overlay: dict | None = None,
) -> dict:
    """Render the head state for one level and project the comparison onto it."""
    head_paths = element_paths(head_ws.get("model", {}))
    base_paths = element_paths(base_ws.get("model", {}))
    own = _own_states(delta)
    by_path = _by_path(head_paths, base_paths)
    encloses = _contains(delta, own, by_path)

    target = container if level == "C3" else system
    # A removed container has no head view, so its own level is rendered from the base and reads as removed.
    gone = target is not None and target not in head_paths and target in base_paths
    source_ws, source_paths = (base_ws, base_paths) if gone else (head_ws, head_paths)
    view = to_react_flow(source_ws, level, system, container, node_overlay, edge_overlay)

    if not gone:
        _replace_placeholders(view["nodes"], delta, source_paths, base_paths, own)

    for node in view["nodes"]:
        info = source_paths.get(node["id"]) or base_paths.get(node["id"]) or {}
        key = (info.get("kind", ""), info.get("path", ""))
        state = dict(own.get(key, _UNCHANGED))
        if gone and state["state"] == "unchanged":
            state = {**_UNCHANGED, "state": "removed", "ghost": True}
        if state["state"] == "unchanged" and key in encloses:
            state = {**state, "state": "modified", "contains_changes": True}
        elif state["state"] == "modified" and key in encloses:
            state = {**state, "contains_changes": True}
        node["data"]["delta"] = state

    present = {n["id"] for n in view["nodes"]}
    if not gone:
        view["nodes"].extend(_ghosts(delta, level, target, head_paths, base_paths, own, present))

    node_paths = {
        n["id"]: (source_paths.get(n["id"]) or base_paths.get(n["id"]) or {}).get("path", "")
        for n in view["nodes"]
    }
    edge_states = _edge_states(delta)
    for edge in view["edges"]:
        key = (node_paths.get(edge["source"], ""), node_paths.get(edge["target"], ""))
        state = edge_states.get(key, {"state": "unchanged", "fields": [], "ghost": False})
        if gone:
            state = {"state": "removed", "fields": [], "ghost": True}
        edge["data"]["delta"] = state
    if not gone:
        view["edges"].extend(_ghost_edges(delta, node_paths))

    changes = _changes(delta, by_path)
    added = len(delta.added) + len(delta.edges_added)
    removed = len(delta.removed) + len(delta.edges_removed)
    changed = len(delta.changed) + len(delta.edges_changed)
    view["summary"] = {
        "added": added, "removed": removed, "changed": changed,
        "empty": not (added or removed or changed), "changes": changes,
    }
    return view
