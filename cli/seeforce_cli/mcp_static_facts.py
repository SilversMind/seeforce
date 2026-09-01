# See mcp/static_facts.py for the @c3:component annotation — this file is a live
# shipped-package twin, not separately annotated, matching this repo's convention for
# the other mcp/*.py <-> mcp_*.py pairs (e.g. mcp/server.py vs mcp_server.py).
# Annotating both would produce two same-named components in the same container.


def collapse_to_components(facts: list, ws: dict, infer_owner) -> list[dict]:
    """
    facts: list of FileFacts-shaped objects (from c4parser.static_facts.extract_facts)
    ws: workspace dict (from fetch_workspace())
    infer_owner: infer_owner(file_path, ws) -> dict, matching ownership.py's signature

    Returns one dict per surviving candidate edge: from_file, from_component,
    raw_import, to_file, to_component. Intra-component edges (both endpoints
    resolve to the same known component) are dropped. When either endpoint's
    owner is unknown (no annotations yet — cold start), the edge is kept with
    component=None: there's nothing to collapse against yet, so it passes
    through as a raw recall signal.
    """
    edges: list[dict] = []
    for file_facts in facts:
        from_owner = infer_owner(file_facts.file, ws)
        from_component = from_owner["element"]["name"] if from_owner["element"] else None

        for imp in file_facts.imports:
            to_component = None
            if imp.resolved_path is not None:
                to_owner = infer_owner(imp.resolved_path, ws)
                to_component = to_owner["element"]["name"] if to_owner["element"] else None
                if from_component is not None and from_component == to_component:
                    continue

            edges.append({
                "from_file": file_facts.file,
                "from_component": from_component,
                "raw_import": imp.raw,
                "to_file": imp.resolved_path,
                "to_component": to_component,
            })

    return edges
