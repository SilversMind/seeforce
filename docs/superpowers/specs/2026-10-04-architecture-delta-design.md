# Architecture delta — design

**Date:** 2026-10-04
**Status:** approved, pending implementation plan
**Branch:** `feat/arch-delta`

## Purpose

Answer one question: **what did this branch change at the architecture level?**

The primary consumer is an AI assistant, through a new MCP tool. It calls the delta before
finishing a task, to judge whether the C4 annotations still match what the code does — the same
moment the `seeforce-arch-check` skill runs today, but comparing two snapshots instead of
inspecting one. The `seeforce delta` CLI command is the secondary surface, for a human or a CI job.

Success: an assistant that just edited annotated files can see, in one call, which elements and
relations its branch added, removed, or altered — including renames, and without a false cascade
of edge changes.

This is rung 1 of the ladder recorded in the 2026-09-29 competitor research (a markdown change
list, `+ / ~ / −`, grouped by element kind), plus the three-counter summary line from rung 2, which
is nearly free once rung 1 exists.

## Scope

In:

- A pure comparison over two `workspace.json` structures, returning a serialisable result
- A markdown renderer over that result
- An MCP tool returning the markdown
- A `seeforce delta` CLI command, with `--json` for the raw structure

Out, deliberately:

- Any graph rendering, phantom overlay, or Before/Delta/After tabs (rungs 3–4)
- The self-overwriting PR bot comment (rung 2's delivery shape)
- A backend endpoint
- "Moved between containers" classification
- Any risk, impact, or merge-safety score — authored facts only
- Writing any file to disk

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Primary consumer | MCP tool; CLI second | The assistant is who asks the question, at the end of a task |
| Inputs | Git revisions | `git show <rev>:.seeforce/workspace.json`; head defaults to the working tree |
| Pairing key | `(kind, source_file)` bucket, name within a bucket, id when no `source_file` | Survives renames without authored ids or similarity heuristics |
| Changed fields | All, named individually | No hard-coded judgment about which field deserves attention |
| Edge comparison | Both endpoints resolved to pairing keys first | Stops a rename producing N false edge changes |
| Placement | `packages/c4parser/c4parser/delta.py` | Both the CLI and the backend already depend on this package |
| MCP return | Markdown | The assistant reads the delta to judge it; JSON costs tokens for no new capability |
| JSON access | `--json` on the CLI only | The non-LLM consumers are Python and import the dataclasses directly |

### Why `source_file` and not the id

Ids are derived from names (`seeforce-frontend-lexicon`, `rel-<src>-<dst>`), so a rename produces
a new id and a naive diff reads it as remove + add. Pairing on `source_file` sidesteps this with no
authored ids and no fuzzy matching.

Measured on the current `workspace.json` (32 elements, 27 distinct `source_file`):

- 2 systems (`SeeForce`, `GitHub`) carry no `source_file` → they pair by id
- `backend/c4_project/__init__.py` carries 2 elements of different kinds (container + person) → the
  kind in the key separates them
- `cli/seeforce_cli/mcp_server.py` carries 3 elements, **two of them components** → `(kind,
  source_file)` is not unique, hence the within-bucket fallback

So: a bucket holding exactly one element on each side pairs directly, and a rename there is
reported as a rename. A bucket holding several pairs by name, and a rename inside such a file
degrades to remove + add. The degradation is local and explainable, and it currently affects one
file.

## Structure

`packages/c4parser/c4parser/delta.py`, beside `builder.py`:

- `flatten(ws) -> list[Element]` — walks `model.people` and
  `model.softwareSystems[].containers[].components[]`, producing flat records that carry the kind,
  the pairing key, the display path (`Lexicon (Frontend)`), the compared fields, and the raw
  relations.
- `pair(base, head) -> tuple[list[Pair], list[Element], list[Element]]` — applies the bucket rule
  above, returning matched pairs plus the unmatched on each side (added / removed).
- `diff(base_ws, head_ws) -> Delta` — the result: added, removed, and changed elements, and added,
  removed, and changed relations. A changed element carries a list of `(field, before, after)`.
  Dataclasses, so `dataclasses.asdict` serialises them.
- `render_markdown(delta) -> str` — one renderer over `Delta`. Never an intermediate format.

Relations are compared after both endpoints are resolved through the same pairing, so an edge is
keyed by `(source pairing key, destination pairing key)` rather than by its derived id.

`cli/seeforce_cli/commands/delta.py` stays thin: resolve the revisions, load the two JSON
documents, call `diff`, print `render_markdown` or, with `--json`, the serialised structure. Exit
code 0 regardless of what changed.

The MCP tool `get_architecture_delta(base_rev: str = "main")` lives in
`cli/seeforce_cli/mcp_server.py` as a new handler, decorated with `_diagnosable` like the others.
It reads `.seeforce/workspace.json` from the given revision and from the working tree, both under
`resolve_project_root()`.

Note a property worth keeping: this tool needs no backend and no token. It is the first seeforce
MCP tool that works fully offline, so it cannot fail from the backend-state and project-id problems
that broke every other tool on 2026-10-04.

## Output

```markdown
## Architecture delta

2 added, 1 removed, 3 changed

### Components
+ Delta Reporter (c4parser) — packages/c4parser/c4parser/delta.py
− Upload Panel (Frontend) — frontend/src/components/UploadPanel.tsx
~ Tool Handlers (MCP Server) — description
~ Lexicon (Frontend) — renamed from "Glossary"; technology: SWR → TanStack Query

### Relationships
+ Delta Reporter → Annotation Parser: "reads the two workspace snapshots"
− Frontend → Backend: "uploads workspace.json"
~ MCP Server → Backend: description
```

Output is English, matching the existing MCP tools, the annotations, and the README.

Short field values are shown as `before → after`. Long ones (`description`) name the field only, to
keep one change on one line. No output beyond the heading when nothing changed; the command says so
in a single line.

## Errors

Each case produces one explanatory line, never a traceback:

- The revision does not exist — surface git's own message
- `.seeforce/workspace.json` absent at that revision (the file predates it, or the project was
  never scanned)
- Either document is not valid JSON
- Either document lacks the expected `model` shape

## Testing

Pure-function tests over small hand-built dictionaries, one behaviour each:

- An added element, a removed element
- A changed element, one test per compared field
- A rename detected through `source_file` in a single-element bucket
- A rename inside `mcp_server.py`'s multi-component bucket, asserted to degrade to remove + add
- An added relation, a removed relation, a changed relation description
- A renamed element asserted **not** to mark its inbound relations as changed — the cascade guard
- An element with no `source_file` paired by id

Plus two tests against the repository's real `.seeforce/workspace.json`: compared against itself it
yields an empty delta, and `flatten` finds the 32 elements the file holds.

CLI tests cover the revision-resolution and the error lines; the MCP tool gets one test asserting it
returns the markdown rather than raising, matching the existing pattern in
`cli/tests/test_mcp_static_facts_tool.py`.
