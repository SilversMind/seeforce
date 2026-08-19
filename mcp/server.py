#!/usr/bin/env python3
"""
@c2:container
name: MCP Server
system: SeeForce
technology: Python / MCP stdio
description: Exposes SeeForce architecture context to AI coding assistants (Claude Code, Cursor, etc.) via the Model Context Protocol over stdio. Provides tools to query containers, components, and file ownership without reading source files.
uses:
  - Backend: "Fetches workspace architecture data via REST API"
    technology: REST
"""
"""
SeeForce MCP Server — exposes architecture context to Claude Code and other AI assistants.

Configuration (env vars):
  SEEFORCE_API_URL      Base URL of SeeForce backend  (default: http://localhost:8000)
  SEEFORCE_PROJECT_ID   Project UUID. Falls back to nearest .c4project file.
  SEEFORCE_API_TOKEN    Optional Bearer token for authenticated instances.

Add to .claude/settings.json in your project:
  {
    "mcpServers": {
      "seeforce": {
        "command": "python",
        "args": ["/path/to/seeforce/mcp/server.py"],
        "env": {
          "SEEFORCE_API_URL": "https://your-seeforce.example.com",
          "SEEFORCE_PROJECT_ID": "your-project-uuid"
        }
      }
    }
  }
"""

import asyncio
import os
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL = os.environ.get("SEEFORCE_API_URL", "http://localhost:8000").rstrip("/")
API_TOKEN = os.environ.get("SEEFORCE_API_TOKEN", "")
_PROJECT_ID_ENV = os.environ.get("SEEFORCE_PROJECT_ID", "")


def _resolve_project_id() -> str:
    if _PROJECT_ID_ENV:
        return _PROJECT_ID_ENV
    path = Path.cwd()
    for _ in range(8):
        candidate = path / ".c4project"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
        if path.parent == path:
            break
        path = path.parent
    return ""


def _http_headers() -> dict:
    h: dict = {}
    if API_TOKEN:
        h["Authorization"] = f"Token {API_TOKEN}"
    return h


# ---------------------------------------------------------------------------
# Workspace fetching
# ---------------------------------------------------------------------------

async def _fetch_workspace() -> dict:
    """Return the workspace source_json for the configured project."""
    project_id = _resolve_project_id()
    async with httpx.AsyncClient(base_url=API_URL, headers=_http_headers(), timeout=15) as client:
        if project_id:
            # List to find numeric pk, then fetch detail for source_json
            r = await client.get("/api/graph/")
            r.raise_for_status()
            projects = r.json()
            if not isinstance(projects, list):
                projects = [projects]
            match_meta = next((p for p in projects if p.get("project_id") == project_id), None)
            if not match_meta and projects:
                match_meta = projects[0]
            if not match_meta:
                raise ValueError(f"No project found with id {project_id!r}")
            pk = match_meta["id"]
            r2 = await client.get(f"/api/graph/{pk}/")
            r2.raise_for_status()
            match = r2.json()
        else:
            r = await client.get("/api/graph/latest/")
            r.raise_for_status()
            match = r.json()

    return match.get("source_json", {})


# ---------------------------------------------------------------------------
# Workspace navigation helpers
# ---------------------------------------------------------------------------

def _all_systems(ws: dict) -> list[dict]:
    return ws.get("model", {}).get("softwareSystems", [])


def _all_containers(ws: dict) -> list[dict]:
    result = []
    for sys in _all_systems(ws):
        for cont in sys.get("containers", []):
            result.append({**cont, "_system": sys["name"]})
    return result


def _all_components(ws: dict) -> list[dict]:
    result = []
    for sys in _all_systems(ws):
        for cont in sys.get("containers", []):
            for comp in cont.get("components", []):
                result.append({**comp, "_container": cont["name"], "_system": sys["name"]})
    return result


def _external_systems(ws: dict) -> list[dict]:
    return [s for s in _all_systems(ws) if "External" in s.get("tags", "")]


def _id_to_name(dest_id: str, ws: dict) -> str:
    for el in _all_systems(ws) + _all_containers(ws) + _all_components(ws):
        if el.get("id") == dest_id:
            return el.get("name", dest_id)
    return dest_id


def _format_rel(rel: dict, ws: dict) -> str:
    name = _id_to_name(rel.get("destinationId", ""), ws)
    desc = rel.get("description", "")
    tech = rel.get("technology", "")
    tech_str = f" [{tech}]" if tech else ""
    return f"→ {name}{tech_str}: {desc}" if desc else f"→ {name}{tech_str}"


# ---------------------------------------------------------------------------
# File ownership inference
# ---------------------------------------------------------------------------

def _path_dir_distance(a: str, b: str) -> int:
    """Directory-level distance between two paths via common ancestor."""
    pa = Path(a).resolve().parent.parts
    pb = Path(b).resolve().parent.parts
    common = sum(1 for x, y in zip(pa, pb) if x == y)
    return (len(pa) - common) + (len(pb) - common)


def _infer_owner(file_path: str, ws: dict) -> dict:
    """
    Return ownership info for a file.
    Result keys: confidence, kind ("component"|"container"|None), element, candidates
    """
    fp = Path(file_path)
    try:
        fp_abs = fp.resolve()
    except Exception:
        fp_abs = fp

    comps = _all_components(ws)
    conts = _all_containers(ws)

    # 1. Exact match on source_file
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

    # 4. Container only — find closest by path distance
    best, best_dist = None, 999
    for cont in conts:
        sf = cont.get("source_file", "")
        if not sf:
            continue
        d = _path_dir_distance(str(fp_abs), sf)
        if d < best_dist:
            best_dist, best = d, cont
    if best and best_dist < 8:
        comps_in = [c for c in comps if c.get("_container") == best["name"]]
        return {"confidence": "container_only", "kind": "container", "element": best, "candidates": comps_in}

    return {"confidence": "unknown", "kind": None, "element": None, "candidates": []}


def _render_owner(file_path: str, result: dict, ws: dict) -> str:
    conf = result["confidence"]
    el = result.get("element")
    lines = [f"File: {file_path}", f"Confidence: {conf}"]

    if not el:
        lines.append("No C4 annotation found in directory tree.")
        lines.append("\nAll known containers:")
        for cont in _all_containers(ws):
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
                lines.append(f"  {_format_rel(rel, ws)}")
        extras = [c for c in result.get("candidates", []) if c.get("id") != el.get("id")]
        if extras:
            lines.append("Other components in same directory:")
            for c in extras:
                lines.append(f"  - {c['name']}")
    elif kind == "container":
        lines.append(f"Container: **{el['name']}** ({el.get('technology', '')})")
        comps_in = [c for c in _all_components(ws) if c.get("_container") == el["name"]]
        if comps_in:
            lines.append("C3 components in this container:")
            for c in comps_in:
                desc_short = (c.get("description") or "")[:70]
                lines.append(f"  - {c['name']}: {desc_short}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

server = MCPServer("SeeForce")


@server.tool()
async def get_context() -> str:
    """
    Returns a high-level overview of the project architecture: systems, containers,
    technologies, descriptions, and C2-level relationships. Call this at the start of
    a session to understand the architecture before implementing anything.
    """
    ws = await _fetch_workspace()
    lines: list[str] = [f"# Architecture: {ws.get('name', 'Unknown')}\n"]

    internals = [s for s in _all_systems(ws) if "External" not in s.get("tags", "")]
    for sys in internals:
        lines.append(f"## System: {sys['name']}")
        if sys.get("description"):
            lines.append(sys["description"])
        for cont in sys.get("containers", []):
            tech = f" ({cont['technology']})" if cont.get("technology") else ""
            lines.append(f"\n### Container: {cont['name']}{tech}")
            if cont.get("description"):
                lines.append(cont["description"])
            rels = cont.get("relationships", [])
            if rels:
                lines.append("Uses:")
                for rel in rels:
                    lines.append(f"  {_format_rel(rel, ws)}")
        lines.append("")

    externals = _external_systems(ws)
    if externals:
        lines.append("## External Systems")
        for ext in externals:
            lines.append(f"- **{ext['name']}**: {ext.get('description', '')}")

    return "\n".join(lines)


@server.tool()
async def find_component(query: str) -> str:
    """
    Search for a C4 component or container by name or keyword.
    Returns matching elements with description, technology, source file, and edges.
    Use when you need to know where a specific concern lives in the architecture.
    Example: 'auth', 'email', 'game session', 'cache'
    """
    ws = await _fetch_workspace()
    q = query.lower()
    results: list[tuple[int, str, dict]] = []

    for comp in _all_components(ws):
        score = 0
        if q in comp.get("name", "").lower():
            score += 10
        for word in q.split():
            if word in comp.get("description", "").lower():
                score += 1
        if score:
            results.append((score, "component", comp))

    for cont in _all_containers(ws):
        score = 0
        if q in cont.get("name", "").lower():
            score += 10
        for word in q.split():
            if word in cont.get("description", "").lower():
                score += 1
        if score:
            results.append((score, "container", cont))

    results.sort(key=lambda x: x[0], reverse=True)

    if not results:
        return f"No components or containers found matching '{query}'."

    lines = [f"Found {len(results)} match(es) for '{query}':\n"]
    for i, (_, kind, el) in enumerate(results[:8], 1):
        container_hint = f" in {el['_container']}" if kind == "component" else f" (system: {el.get('_system', '?')})"
        lines.append(f"### {i}. {el['name']} [{kind}{container_hint}]")
        if el.get("technology"):
            lines.append(f"Technology: {el['technology']}")
        if el.get("description"):
            lines.append(f"Description: {el['description']}")
        if el.get("source_file"):
            lines.append(f"Source: {el['source_file']}")
        rels = el.get("relationships", [])
        if rels:
            lines.append("Uses:")
            for rel in rels:
                lines.append(f"  {_format_rel(rel, ws)}")
        lines.append("")

    return "\n".join(lines)


@server.tool()
async def get_file_owner(file_path: str) -> str:
    """
    Given a file path, returns which C4 component or container owns it.
    Works for unannotated files via directory proximity inference.
    Returns the component's responsibility, existing edges, and confidence level.
    Use when starting to edit a file to understand its architectural context.
    """
    ws = await _fetch_workspace()
    result = _infer_owner(file_path, ws)
    return _render_owner(file_path, result, ws)


@server.tool()
async def get_architecture_for_files(file_paths: list[str]) -> str:
    """
    Given a list of modified or created files, returns architectural context for each:
    which component owns it, existing edges, and a flag if the file has no annotation.
    Call after implementing a feature to check whether the C4 architecture needs updating.
    """
    ws = await _fetch_workspace()
    known_externals = [e["name"] for e in _external_systems(ws)]
    sections: list[str] = []

    for fp in file_paths:
        result = _infer_owner(fp, ws)
        has_annotation = result["confidence"] == "exact"
        section = [
            f"=== {fp} ===",
            f"Annotation present: {'yes' if has_annotation else 'no'}",
            _render_owner(fp, result, ws),
        ]
        if not has_annotation and result["confidence"] != "unknown":
            section.append(
                "\n⚠ No annotation on this file. Consider whether it introduces:\n"
                "  • A new named responsibility → new @c3:component\n"
                "  • A new external service dependency → new @c1:external + uses: edge\n"
                "  • A new cross-container relationship → new uses: entry on existing component"
            )
        sections.append("\n".join(section))

    if known_externals:
        sections.append(f"Known external systems in this project: {', '.join(known_externals)}")

    return "\n\n".join(sections) if sections else "No files provided."


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(server.run_stdio_async())
