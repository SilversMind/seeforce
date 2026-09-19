"""
@c3:component
name: Ownership Inference
container: MCP Server
technology: Python
description: Infers which C4 component or container owns a given file path — via exact source_file match, same-directory proximity, or nearest-parent-directory fallback when nothing is annotated yet.
"""
"""File → C4 component/container ownership inference."""

from pathlib import Path

from seeforce_cli.mcp_workspace import all_components, all_containers, format_rel


def _dir_distance(a: str, b: str) -> int:
    pa = Path(a).resolve().parent.parts
    pb = Path(b).resolve().parent.parts
    common = sum(1 for x, y in zip(pa, pb) if x == y)
    return (len(pa) - common) + (len(pb) - common)


def infer_owner(file_path: str, ws: dict) -> dict:
    """
    Return ownership info for a file.
    Keys: confidence, kind ("component"|"container"|None), element, candidates
    """
    fp = Path(file_path)
    try:
        fp_abs = fp.resolve()
    except Exception:
        fp_abs = fp

    comps = all_components(ws)
    conts = all_containers(ws)

    # 1. Exact match
    for comp in comps:
        sf = comp.get("source_file", "")
        if sf and Path(sf).resolve() == fp_abs:
            return {"confidence": "exact", "kind": "component", "element": comp, "candidates": [comp]}
    for cont in conts:
        sf = cont.get("source_file", "")
        if sf and Path(sf).resolve() == fp_abs:
            return {"confidence": "exact", "kind": "container", "element": cont, "candidates": [cont]}

    # 2. Same directory
    fp_dir = fp_abs.parent
    same_dir = [c for c in comps if c.get("source_file") and Path(c["source_file"]).resolve().parent == fp_dir]
    if same_dir:
        return {"confidence": "same_dir", "kind": "component", "element": same_dir[0], "candidates": same_dir}
    same_dir_cont = [c for c in conts if c.get("source_file") and Path(c["source_file"]).resolve().parent == fp_dir]
    if same_dir_cont:
        return {"confidence": "same_dir", "kind": "container", "element": same_dir_cont[0], "candidates": same_dir_cont}

    # 3. Walk up directory tree
    for parent in fp_abs.parents:
        near_comps = [c for c in comps if c.get("source_file") and Path(c["source_file"]).resolve().parent == parent]
        if near_comps:
            return {"confidence": "nearest_parent", "kind": "component", "element": near_comps[0], "candidates": near_comps}
        near_conts = [c for c in conts if c.get("source_file") and Path(c["source_file"]).resolve().parent == parent]
        if near_conts:
            return {"confidence": "nearest_parent", "kind": "container", "element": near_conts[0], "candidates": near_conts}

    # 4. Closest container by path distance
    best, best_dist = None, 999
    for cont in conts:
        sf = cont.get("source_file", "")
        if not sf:
            continue
        d = _dir_distance(str(fp_abs), sf)
        if d < best_dist:
            best_dist, best = d, cont
    if best and best_dist < 8:
        return {"confidence": "container_only", "kind": "container", "element": best,
                "candidates": [c for c in comps if c.get("_container") == best["name"]]}

    return {"confidence": "unknown", "kind": None, "element": None, "candidates": []}


def render_owner(file_path: str, result: dict, ws: dict) -> str:
    conf = result["confidence"]
    el = result.get("element")
    lines = [f"File: {file_path}", f"Confidence: {conf}"]

    if not el:
        lines.append("No C4 annotation found in directory tree.")
        lines.append("\nAll known containers:")
        for cont in all_containers(ws):
            lines.append(f"  - {cont['name']} ({cont.get('technology', '')})")
        return "\n".join(lines)

    kind = result["kind"]
    if kind == "component":
        lines.append(f"Owner: **{el['name']}** [component in {el.get('_container', '?')}]")
        if el.get("source_file"):
            lines.append(f"Annotated at: {el['source_file']}")
        if el.get("description"):
            lines.append(f"Responsibility: {el['description']}")
        rels = el.get("relationships", [])
        if rels:
            lines.append("Existing edges:")
            for rel in rels:
                lines.append(f"  {format_rel(rel, ws)}")
        extras = [c for c in result.get("candidates", []) if c.get("id") != el.get("id")]
        if extras:
            lines.append("Other components in same directory:")
            for c in extras:
                lines.append(f"  - {c['name']}")
    elif kind == "container":
        lines.append(f"Container: **{el['name']}** ({el.get('technology', '')})")
        comps_in = [c for c in all_components(ws) if c.get("_container") == el["name"]]
        if comps_in:
            lines.append("C3 components in this container:")
            for c in comps_in:
                lines.append(f"  - {c['name']}: {(c.get('description') or '')[:70]}")

    return "\n".join(lines)
