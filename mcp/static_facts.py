"""
@c3:component
name: Static Facts Bridge
container: MCP Server
technology: Python
description: Collapses the file-level import graph from Static Facts Extractor into component-level candidate edges by resolving each endpoint through file ownership inference, dropping intra-component pairs so only cross-component candidates reach the LLM. Receives already-extracted facts as a parameter — it never calls the extractor itself.
"""


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
