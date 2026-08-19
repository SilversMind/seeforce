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
  SEEFORCE_API_TOKEN    Optional token for authenticated instances.

Add to ~/.claude.json mcpServers (or use `claude mcp add`):
  {
    "seeforce": {
      "type": "stdio",
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/seeforce/mcp/server.py"],
      "env": { "SEEFORCE_API_URL": "https://your-seeforce.example.com" }
    }
  }

Each project repo should contain a .c4project file with its project UUID.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.mcpserver import MCPServer  # noqa: E402

from client import fetch_workspace  # noqa: E402
from ownership import infer_owner, render_owner  # noqa: E402
from workspace import all_components, all_containers, all_systems, external_systems, format_rel  # noqa: E402

server = MCPServer("SeeForce")


@server.tool()
async def get_context() -> str:
    """
    Returns a high-level overview of the project architecture: systems, containers,
    technologies, descriptions, and C2-level relationships. Call this at the start of
    a session to understand the architecture before implementing anything.
    """
    ws = await fetch_workspace()
    lines: list[str] = [f"# Architecture: {ws.get('name', 'Unknown')}\n"]

    for sys in [s for s in all_systems(ws) if "External" not in s.get("tags", "")]:
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
                    lines.append(f"  {format_rel(rel, ws)}")
        lines.append("")

    externals = external_systems(ws)
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
    ws = await fetch_workspace()
    q = query.lower()
    results: list[tuple[int, str, dict]] = []

    for comp in all_components(ws):
        score = 0
        if q in comp.get("name", "").lower():
            score += 10
        for word in q.split():
            if word in comp.get("description", "").lower():
                score += 1
        if score:
            results.append((score, "component", comp))

    for cont in all_containers(ws):
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
                lines.append(f"  {format_rel(rel, ws)}")
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
    ws = await fetch_workspace()
    return render_owner(file_path, infer_owner(file_path, ws), ws)


@server.tool()
async def get_architecture_for_files(file_paths: list[str]) -> str:
    """
    Given a list of modified or created files, returns architectural context for each:
    which component owns it, existing edges, and a flag if the file has no annotation.
    Call after implementing a feature to check whether the C4 architecture needs updating.
    """
    ws = await fetch_workspace()
    known_externals = [e["name"] for e in external_systems(ws)]
    sections: list[str] = []

    for fp in file_paths:
        result = infer_owner(fp, ws)
        has_annotation = result["confidence"] == "exact"
        section = [
            f"=== {fp} ===",
            f"Annotation present: {'yes' if has_annotation else 'no'}",
            render_owner(fp, result, ws),
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


if __name__ == "__main__":
    asyncio.run(server.run_stdio_async())
