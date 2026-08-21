"""
SeeForce MCP Server — exposes architecture context to Claude Code and other AI assistants.

Configuration (env vars):
  SEEFORCE_API_URL      Base URL of SeeForce backend  (default: https://seeforce.onrender.com)
  SEEFORCE_PROJECT_ID   Project UUID. Falls back to nearest .c4project file.
  SEEFORCE_API_TOKEN    Optional token for authenticated instances.

Add to ~/.claude.json mcpServers (or use `claude mcp add`):
  {
    "seeforce": {
      "type": "stdio",
      "command": "seeforce-mcp",
      "env": { "SEEFORCE_API_URL": "https://your-seeforce.example.com" }
    }
  }

Each project repo should contain a .c4project file with its project UUID.
"""

import asyncio
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from seeforce_cli.mcp_client import fetch_workspace
from seeforce_cli.mcp_ownership import infer_owner, render_owner
from seeforce_cli.mcp_workspace import all_components, all_containers, all_systems, external_systems, format_rel

_PROMPT_PATH = Path(__file__).parent / "prompts" / "c4_annotator.md"
_SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".java", ".go", ".cs", ".rb", ".rs"}
_EXCLUDE_DIRS = {"node_modules", "__pycache__", ".git", "dist", "build", "vendor", ".venv", "venv", ".env", "tests"}

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


@server.tool()
async def annotate_codebase() -> str:
    """
    Returns the SeeForce C4 annotation guide and all source files from the current project.
    Call this when the user asks to annotate their codebase with C4 architecture markers.
    After receiving the output: follow the guide to add @c1, @c2, @c3 annotations to the
    relevant files. Skip tests, migrations, and config boilerplate. When done, remind the
    user to run: seeforce scan . && git add -A && git commit -m "chore: add C4 annotations"
    """
    prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    cwd = os.getcwd()

    sections: list[str] = []
    total_chars = 0
    MAX_CHARS = 400_000

    for dirpath, dirnames, filenames in os.walk(cwd):
        dirnames[:] = [d for d in dirnames if d not in _EXCLUDE_DIRS]
        for filename in filenames:
            if Path(filename).suffix not in _SOURCE_EXTENSIONS:
                continue
            file_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(file_path, cwd)
            try:
                content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            section = f"### {rel_path}\n```\n{content}\n```\n"
            if total_chars + len(section) > MAX_CHARS:
                sections.append("### ⚠ Remaining files omitted — context limit reached.")
                break
            sections.append(section)
            total_chars += len(section)

    files_block = "\n".join(sections) if sections else "No source files found."
    return f"{prompt}\n\n---\n\n## Source Files\n\n{files_block}"


def main():
    asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
