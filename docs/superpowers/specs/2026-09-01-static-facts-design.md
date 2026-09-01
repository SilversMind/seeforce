# Static Facts (tree-sitter) — Design

## Problem

The C4 annotator LLM prompt (`cli/seeforce_cli/prompts/c4_annotator.md`) infers `uses:` relations purely by reading source files. This works but has two failure modes:

1. **Recall** — a real cross-file relation (import, call) gets missed because the LLM didn't happen to read both sides of it.
2. **Drift detection** (`seeforce-arch-check` skill) — comparing declared annotations against actual code relies entirely on LLM re-reading; there's no cheap structural ground truth to diff against.

Goal: give the LLM an additional, clearly-labeled **candidate signal** — a statically-extracted import graph — without making it a source of truth. The LLM still must verify relations against runtime behavior (dynamic dispatch, DI, config-driven wiring); static facts only reduce missed edges, they never establish that an edge is correct.

## Scope (v1)

- Languages: **Python and TypeScript** (dogfooding target: this repo's `backend/`, `cli/`, `packages/` in Python; `frontend/` in TypeScript).
- Extraction: imports, top-level function/class definitions, and the docstring/comment immediately adjacent to a definition (semantic context — an import graph alone carries no "why").
- Import resolution: heuristic only (dotted/relative path → file, based on detected internal package roots). No full module-resolution algorithm (no `sys.path` emulation, no `tsconfig.json` path-alias resolution) — deferred if it proves necessary.
- Cross-component collapsing (file-level edges → component-level edges) reuses the existing `infer_owner()` file→component mapping in `mcp/ownership.py`, rather than building a new one.

## Non-goals (v1)

- No persisted cache / no new CLI command / no change to `seeforce scan`. Facts are computed on demand, per MCP call, over just the requested files (mirrors `get_architecture_for_files`'s existing call shape).
- No cross-component filtering when no annotations exist yet (cold-start/bootstrap case) — the component lookup is naturally empty, so the filter degrades to a no-op and the raw (noise-filtered) edges pass through. Same code path handles both bootstrap and re-scan; no separate "mode".
- No semantic/type resolution (no LSIF/SCIP-grade precision). Purely syntactic.

## Architecture

### Module layout — isolated, removable

```
packages/c4parser/c4parser/
  static_facts/
    __init__.py     # public interface: extract_facts(files) -> list[FileFacts]
    backend.py       # tree-sitter grammar loading + query execution
    resolver.py       # import string -> repo file path (heuristic, per language)
    types.py            # FileFacts dataclass: file, imports, defines, docstrings
    queries/
      python.scm
      typescript.scm
```

**Isolation rule:** nothing outside `static_facts/` imports `backend.py` or `resolver.py` directly — only `static_facts.extract_facts()`. If tree-sitter needs to be dropped, deleting the `static_facts/` directory leaves `scanner.py`/`builder.py`/`exporter.py` and the existing MCP tools fully functional; only the new MCP tool loses its data source.

**Optional dependency:** `tree-sitter` + `tree-sitter-language-pack` are declared under `[project.optional-dependencies]` (extra: `static-facts`) in `packages/c4parser/pyproject.toml`, not a hard dependency. `static_facts/__init__.py` imports the backend lazily; if the extra isn't installed, `extract_facts()` returns `[]` rather than raising an ImportError that breaks the base package.

### Extraction (`backend.py`)

Minimal hand-written tree-sitter queries per language (not a vendored `tags.scm`) — only the capture types actually needed:
- Python: `import_statement`, `import_from_statement`, `function_definition`, `class_definition`, adjacent `comment`/string-expression-statement docstring.
- TypeScript: `import_statement`, `import_clause`, `function_declaration`, `class_declaration`, adjacent `comment`.

### Resolution (`resolver.py`)

Heuristic only:
- Detect internal package roots by walking for `pyproject.toml`/`package.json` boundaries.
- Python: dotted import path → replace `.` with `/`, relative to detected package root, check for file or `__init__.py`.
- TypeScript: relative imports (`./`, `../`) resolve directly against the importing file's directory; bare specifiers checked against internal package names only (no `node_modules` resolution).
- Unresolved imports are kept as raw strings, classified via the noise filter below, not dropped outright.

### Noise filter + cross-component collapse

Applied after resolution, before the facts leave `static_facts`:
1. Drop imports that are neither internal (resolved to a repo file) nor on a small allowlist of known external services (DB/queue/HTTP client packages) — stdlib and generic libraries are noise.
2. For each surviving edge, map both endpoints to a component via `mcp/ownership.py`'s `infer_owner()`.
3. Drop edges where both endpoints resolve to the same component (intra-component, not architecturally interesting).
4. If `infer_owner()` returns `unknown` for an endpoint (no annotations yet — cold start), keep the edge unresolved-to-component; it still serves as a raw recall signal for initial annotation, just without collapsing.

### MCP exposure

**Correction (found while planning implementation):** `mcp/server.py` (repo root) and `cli/seeforce_cli/mcp_server.py` are two live, independently-deployed copies, not a canonical + stale pair — the root copy is what this repo's own Claude Code session dogfoods against (wired by direct file path), the CLI copy is what ships inside the `seeforce-cli` pip package and runs for real users via the `seeforce-mcp` entry point. They've already drifted (the CLI copy has a 5th tool, `annotate_codebase`, the root copy lacks). The new tool is added to **both**: `cli/seeforce_cli/mcp_server.py` because that's required for any real user to get this feature, and `mcp/server.py` because otherwise this repo's own dogfooding session — the whole motivating use case — never sees it. Same treatment applies to their `ownership.py`/`mcp_ownership.py` siblings, which stay logic-identical (same function signatures) and only differ in import paths (`from workspace import ...` vs `from seeforce_cli.mcp_workspace import ...`).

New tool (added to both `mcp/server.py` and `cli/seeforce_cli/mcp_server.py`):

```python
@server.tool()
async def get_static_facts_for_files(file_paths: list[str]) -> str:
    """
    Given a list of files, returns a statically-extracted candidate signal:
    imports/calls observed in the code, resolved to components where possible,
    plus adjacent docstrings for context.

    This is a CANDIDATE list, not verified truth — it catches relations the
    reader might miss (recall aid), but cannot see dynamic wiring (DI,
    reflection, config-driven routes, message-bus subscriptions) and may
    include edges that are imports-only with no actual call site. Confirm
    each candidate against real usage before treating it as an architectural
    relation.
    """
```

Same call-time, per-file-list shape as `get_architecture_for_files` — no new lifecycle to manage.

### Prompt change

`cli/seeforce_cli/prompts/c4_annotator.md` (the canonical, runtime-used copy — see stale-file note below) Step 6 gets an added paragraph instructing the LLM to cross-check candidate edges from `get_static_facts_for_files` before annotating, treating them as a recall aid and never as sufficient evidence on their own — dynamic wiring must still be searched for independently.

### Known stale/duplicate files

- `backend/c4parser/` is a manually vendored copy of `packages/c4parser/c4parser/` — this change lands only in the canonical `packages/c4parser/c4parser/` location; `backend/c4parser/` is left as-is (already drifting before this change, pre-existing tech debt, not touched by this change).
- `prompts/c4_annotator.md` (repo root) is stale and not used at runtime; the prompt edit in this change targets `cli/seeforce_cli/prompts/c4_annotator.md` only, not touched by this change.
- `mcp/server.py` + `mcp/ownership.py` vs `cli/seeforce_cli/mcp_server.py` + `mcp_ownership.py` — both live (dogfooding vs shipped product, see MCP exposure section above) — **this change touches both**, unlike the two duplicates above.

## Error handling

- `static-facts` extra not installed → `extract_facts()` returns `[]`; MCP tool reports static analysis unavailable rather than failing.
- Per-file parse error (malformed syntax) → caught, file skipped, extraction continues for the rest (mirrors `scanner.py`'s existing per-file try/except).
- Unresolvable import → kept as an unclassified/raw entry where useful (see resolver section), never fatal.

## Testing

- `extract_facts` unit tests against fixture files (Python + TypeScript) covering imports, defs, docstring capture.
- Resolver tests: dotted-path Python resolution, relative TS resolution, unresolved-import fallback.
- Filter tests: cross-component collapse with a populated `workspace.json`, and the cold-start no-op path with an empty one.
- MCP tool test mirroring the existing `get_architecture_for_files` test pattern.

## Open items for the implementation plan

- Exact allowlist of "known external service" package names for the noise filter (Python + TS) — a starting list, extensible later.
- Exact `.scm` query text per language (small, but needs to be written and validated against real repo files).
