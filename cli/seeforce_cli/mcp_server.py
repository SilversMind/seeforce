"""
@c2:container
name: MCP Server
system: SeeForce
technology: Python / MCP stdio
description: Exposes SeeForce architecture context to AI coding assistants (Claude Code, Cursor, etc.) via the Model Context Protocol over stdio — get_context, find_component, get_file_owner, get_architecture_for_files, and annotate_codebase let assistants query containers, components, and file ownership without reading source files. Ships as the seeforce-mcp entry point inside the seeforce-cli pip package.
short_desc: Exposes SeeForce architecture context to AI coding assistants via MCP
uses:
    - Backend: "Fetches workspace architecture data via REST API"
      technology: REST
"""

"""
@c3:component
name: Tool Handlers
container: MCP Server
description: Answers the 5 architecture questions an AI assistant can ask — get_context (system overview), find_component (search by keyword), get_file_owner (which component owns a file), get_architecture_for_files (drift check for edited files), and annotate_codebase (the C4 annotation guide plus source files, for a first-time annotation pass).
short_desc: Implements the 5 MCP tools assistants call to query architecture
uses:
    - Backend: "Fetches workspace architecture data via REST API"
      technology: REST
"""

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
import functools
import os
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer

from c4parser.static_facts import extract_facts
from seeforce_cli.mcp_client import fetch_workspace
from seeforce_cli.mcp_config import API_URL
from seeforce_cli.mcp_ownership import infer_owner, render_owner
from seeforce_cli.mcp_static_facts import collapse_to_components
from seeforce_cli.mcp_workspace import all_components, all_containers, all_systems, external_systems, format_rel

_PROMPT_PATH = Path(__file__).parent / "prompts" / "c4_annotator.md"
_SOURCE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".java", ".go", ".cs", ".rb", ".rs"}
_EXCLUDE_DIRS = {"node_modules", "__pycache__", ".git", "dist", "build", "vendor", ".venv", "venv", ".env", "tests"}

server = MCPServer("SeeForce")


def _diagnosable(fn):
    """Turn a connection/auth failure into an error the calling agent can act
    on, instead of an opaque transport-level "Error executing tool" that
    swallows the actual reason (wrong URL, expired token, backend down).
    Runs at every tool call, so it also catches drift between which
    mcp_server.py is actually running and which repo the agent thinks it's
    talking to — the __file__ line below is what exposes that."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except httpx.HTTPStatusError as exc:
            return (
                f"SeeForce backend returned {exc.response.status_code} from {exc.request.url}. "
                f"Check SEEFORCE_API_URL ({API_URL}) and SEEFORCE_API_TOKEN — this MCP server may be "
                f"pointed at the wrong environment or using an expired token.\n"
                f"Running from: {__file__}"
            )
        except httpx.HTTPError as exc:
            return (
                f"SeeForce backend unreachable at {API_URL}: {exc}. Is it running, and is "
                f"SEEFORCE_API_URL pointed at the right place?\nRunning from: {__file__}"
            )

    return wrapper


@server.tool()
@_diagnosable
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
@_diagnosable
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
@_diagnosable
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
@_diagnosable
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


_MAX_DOC_CHARS = 150


def _summarize_docstring(docstring: str) -> str:
    """One definition must stay one output line. A multi-line docstring dumped raw
    turns a cheap recall signal into a context flood, so keep only the first line,
    truncated."""
    if not docstring:
        return ""
    first = next((line.strip() for line in docstring.splitlines() if line.strip()), "")
    if len(first) > _MAX_DOC_CHARS:
        return first[:_MAX_DOC_CHARS].rstrip() + "…"
    return first


@server.tool()
async def get_static_facts_for_files(file_paths: list[str]) -> str:
    """
    Given a list of files, returns a statically-extracted CANDIDATE signal:
    imports observed in the code, resolved to components where possible, plus
    docstrings for any functions/classes defined in those files.

    This is NOT verified truth — it is a recall aid to catch relations you
    might otherwise miss. It cannot see dynamic wiring (DI, reflection,
    config-driven routes, message-bus subscriptions), and an edge here may be
    import-only with no real call site. Confirm each candidate against actual
    usage in the code before treating it as an architectural relation.
    """
    ws = await fetch_workspace()
    facts = extract_facts(os.getcwd(), file_paths)
    if not facts:
        return "Static analysis unavailable (tree-sitter not installed, or no facts extracted for these files)."

    edges = collapse_to_components(facts, ws, infer_owner)

    lines: list[str] = ["⚠ CANDIDATE signal, not verified truth — confirm before annotating.\n"]
    for file_facts in facts:
        lines.append(f"=== {file_facts.file} ===")
        if file_facts.defines:
            lines.append("Definitions:")
            for d in file_facts.defines:
                summary = _summarize_docstring(d.docstring)
                doc = f" — {summary}" if summary else ""
                lines.append(f"  {d.kind} {d.name}{doc}")
        file_edges = [e for e in edges if e["from_file"] == file_facts.file]
        if file_edges:
            lines.append("Candidate edges:")
            for e in file_edges:
                dest = e["to_component"] or e["to_file"] or e["raw_import"]
                lines.append(f"  → {dest} (import: {e['raw_import']})")
        lines.append("")

    return "\n".join(lines)


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
