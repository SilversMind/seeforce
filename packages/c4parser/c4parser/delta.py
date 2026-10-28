"""
@c3:component
name: Delta Reporter
container: Annotation Parser
technology: Python
description: Compares two workspace.json snapshots and reports what changed at the architecture level — pairs elements on (kind, source_file) so a rename reads as a rename rather than a remove plus an add, resolves relation endpoints through that same pairing so renaming an element does not mark all its inbound edges as changed, and renders the result as markdown. Pure computation over two dicts, with no backend call, no token, nothing written to disk.
short_desc: Compares two workspace snapshots into an architecture delta
"""
from dataclasses import dataclass, field

from .exceptions import C4ValidationError

# "source_file" is reserved for a planned (kind, name) second pairing pass; it never differs today.
COMPARED_FIELDS = ("name", "description", "short_desc", "technology", "tags", "source_file")


@dataclass
class Element:
    """One system, person, container, or component, flattened out of a workspace."""
    kind: str
    name: str
    path: str
    id: str
    source_file: str
    fields: dict[str, str] = field(default_factory=dict)
    relations: list[dict[str, str]] = field(default_factory=list)


def _element(kind: str, raw: dict, path: str) -> Element:
    return Element(
        kind=kind,
        name=raw.get("name", ""),
        path=path,
        id=raw.get("id", ""),
        source_file=raw.get("source_file", "") or "",
        fields={f: raw.get(f, "") or "" for f in COMPARED_FIELDS},
        relations=list(raw.get("relationships") or []),
    )


def flatten(ws: dict) -> list[Element]:
    """Walk people and systems/containers/components into flat records."""
    if not isinstance(ws, dict):
        raise C4ValidationError(f"workspace must be a JSON object, got {type(ws).__name__}")
    model = ws.get("model")
    if not isinstance(model, dict):
        raise C4ValidationError("workspace has no 'model' object")

    out: list[Element] = []
    for person in model.get("people") or []:
        out.append(_element("person", person, person.get("name", "")))
    for system in model.get("softwareSystems") or []:
        out.append(_element("system", system, system.get("name", "")))
        for container in system.get("containers") or []:
            out.append(_element("container", container, f"{container.get('name', '')} ({system.get('name', '')})"))
            for component in container.get("components") or []:
                out.append(_element("component", component, f"{component.get('name', '')} ({container.get('name', '')})"))
    return out


def _bucket(elements: list[Element]) -> dict[tuple[str, str], list[Element]]:
    """Group by (kind, source_file), falling back to the derived id when there is no file."""
    out: dict[tuple[str, str], list[Element]] = {}
    for e in elements:
        key = (e.kind, e.source_file) if e.source_file else (e.kind, f"id:{e.id}")
        out.setdefault(key, []).append(e)
    return out


def pair(
    base: list[Element], head: list[Element]
) -> tuple[list[tuple[Element, Element]], list[Element], list[Element]]:
    """Match base elements to head elements, returning (pairs, added, removed)."""
    pairs: list[tuple[Element, Element]] = []
    added: list[Element] = []
    removed: list[Element] = []

    head_buckets = _bucket(head)
    for key, b_items in _bucket(base).items():
        h_items = head_buckets.pop(key, [])
        # A bucket holding exactly one element on each side pairs directly, which
        # NOTE: lets a rename read as a rename instead of a remove plus an add.
        if len(b_items) == 1 and len(h_items) == 1:
            pairs.append((b_items[0], h_items[0]))
            continue
        by_name = {e.name: e for e in h_items}
        for b in b_items:
            match = by_name.pop(b.name, None)
            if match is not None:
                pairs.append((b, match))
            else:
                removed.append(b)
        added.extend(by_name.values())

    for h_items in head_buckets.values():
        added.extend(h_items)
    return pairs, added, removed


@dataclass
class FieldChange:
    field: str
    before: str
    after: str


@dataclass
class ElementChange:
    path: str
    kind: str
    source_file: str
    fields: list[FieldChange] = field(default_factory=list)


@dataclass
class Edge:
    source_path: str
    dest_path: str
    description: str = ""
    technology: str = ""


@dataclass
class EdgeChange:
    source_path: str
    dest_path: str
    fields: list[FieldChange] = field(default_factory=list)


@dataclass
class Delta:
    added: list[Element] = field(default_factory=list)
    removed: list[Element] = field(default_factory=list)
    changed: list[ElementChange] = field(default_factory=list)
    edges_added: list[Edge] = field(default_factory=list)
    edges_removed: list[Edge] = field(default_factory=list)
    edges_changed: list[EdgeChange] = field(default_factory=list)


def _changed_fields(before: Element, after: Element) -> list[FieldChange]:
    return [
        FieldChange(f, before.fields.get(f, ""), after.fields.get(f, ""))
        for f in COMPARED_FIELDS
        if before.fields.get(f, "") != after.fields.get(f, "")
    ]


def _canonical_ids(
    pairs: list[tuple[Element, Element]], added: list[Element], removed: list[Element]
) -> dict[str, str]:
    """Map every element id to one token, shared by a paired base and head element."""
    canon: dict[str, str] = {}
    for b, h in pairs:
        if b.id:
            canon[b.id] = h.path
        if h.id:
            canon[h.id] = h.path
    for e in (*added, *removed):
        if e.id:
            canon[e.id] = e.path
    return canon


def _edges(elements: list[Element], canon: dict[str, str]) -> dict[tuple[str, str], Edge]:
    """Key each relation by its endpoints' canonical tokens, not by its derived id."""
    # Keyed by (source, dest), so two relations between one pair collapse; build rejects that input.
    out: dict[tuple[str, str], Edge] = {}
    for e in elements:
        src = canon.get(e.id) or e.path
        for rel in e.relations:
            raw_dest = rel.get("destinationId", "") or ""
            dest = canon.get(raw_dest) or raw_dest or "?"
            out[(src, dest)] = Edge(
                source_path=src,
                dest_path=dest,
                description=rel.get("description", "") or "",
                technology=rel.get("technology", "") or "",
            )
    return out


def diff(base_ws: dict, head_ws: dict) -> Delta:
    """Compare two workspaces into a Delta of elements and relations."""
    base = flatten(base_ws)
    head = flatten(head_ws)
    pairs, added, removed = pair(base, head)

    changed: list[ElementChange] = []
    for b, h in pairs:
        fields = _changed_fields(b, h)
        if fields:
            changed.append(ElementChange(path=h.path, kind=h.kind, source_file=h.source_file, fields=fields))

    canon = _canonical_ids(pairs, added, removed)
    base_edges = _edges(base, canon)
    head_edges = _edges(head, canon)

    edges_added = [e for key, e in head_edges.items() if key not in base_edges]
    edges_removed = [e for key, e in base_edges.items() if key not in head_edges]
    edges_changed: list[EdgeChange] = []
    for key, head_edge in head_edges.items():
        base_edge = base_edges.get(key)
        if base_edge is None:
            continue
        fields = [
            FieldChange(name, getattr(base_edge, name), getattr(head_edge, name))
            for name in ("description", "technology")
            if getattr(base_edge, name) != getattr(head_edge, name)
        ]
        if fields:
            edges_changed.append(EdgeChange(key[0], key[1], fields))

    return Delta(
        added=added,
        removed=removed,
        changed=changed,
        edges_added=edges_added,
        edges_removed=edges_removed,
        edges_changed=edges_changed,
    )


_MAX_INLINE_VALUE = 60
_KIND_HEADINGS = (
    ("system", "Systems"),
    ("person", "People"),
    ("container", "Containers"),
    ("component", "Components"),
)


def _render_field(change: FieldChange) -> str:
    if change.field == "name":
        return f'renamed from "{change.before}"'
    if len(change.before) > _MAX_INLINE_VALUE or len(change.after) > _MAX_INLINE_VALUE:
        return change.field
    return f"{change.field}: {change.before} → {change.after}"


def render_markdown(delta: Delta) -> str:
    """Render a Delta as the markdown change list. One renderer over the structure."""
    added = len(delta.added) + len(delta.edges_added)
    removed = len(delta.removed) + len(delta.edges_removed)
    changed = len(delta.changed) + len(delta.edges_changed)
    if not (added or removed or changed):
        return "## Architecture delta\n\nNo architecture changes."

    lines = [
        "## Architecture delta",
        "",
        f"{added} added, {removed} removed, {changed} changed",
    ]

    for kind, heading in _KIND_HEADINGS:
        rows: list[str] = []
        for e in delta.added:
            if e.kind == kind:
                rows.append(f"+ {e.path}{f' — {e.source_file}' if e.source_file else ''}")
        for e in delta.removed:
            if e.kind == kind:
                rows.append(f"− {e.path}{f' — {e.source_file}' if e.source_file else ''}")
        for c in delta.changed:
            if c.kind == kind:
                rows.append(f"~ {c.path} — {'; '.join(_render_field(f) for f in c.fields)}")
        if rows:
            lines += ["", f"### {heading}", *rows]

    edge_rows: list[str] = []
    for e in delta.edges_added:
        edge_rows.append(f'+ {e.source_path} → {e.dest_path}: "{e.description}"')
    for e in delta.edges_removed:
        edge_rows.append(f'− {e.source_path} → {e.dest_path}: "{e.description}"')
    for c in delta.edges_changed:
        edge_rows.append(f"~ {c.source_path} → {c.dest_path}: {'; '.join(_render_field(f) for f in c.fields)}")
    if edge_rows:
        lines += ["", "### Relationships", *edge_rows]

    return "\n".join(lines)
