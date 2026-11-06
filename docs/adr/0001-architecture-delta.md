# 1. Architecture delta: how two baselines are compared

Date: 2026-10-28

## Status

Accepted.

## Context

Comparing two `.seeforce/workspace.json` baselines tells a reviewer what a change did to the
declared architecture without reading the whole diff. Four decisions in that comparison are not
obvious from the code and would be re-litigated without a record.

## Decisions

### Elements are paired on kind and declaring file, not on their identifier

Identifiers are derived from names — `seeforce-frontend-lexicon` — so renaming an element produces a
new identifier, and an identifier-keyed diff reports a rename as a removal plus an addition. Pairing
on `(kind, source_file)` survives the rename, so it is reported as a modification of the `name`
field. No authored identifiers are needed.

The cost: one file declaring several elements of the same kind breaks the key's uniqueness.
`cli/seeforce_cli/mcp_server.py` holds two components today. Inside such a file the comparison falls
back to matching by name, and a rename there does degrade to removal plus addition. The output says
so rather than leaving the reader to infer it.

Rejected: adding an optional authored `id:` to annotations. It removes the limitation at the root and
remains the eventual fix, but it is a change to the annotation format and to every consumer of a
derived id, for a degradation that currently affects one file.

### The counters include relation changes

The three counters cover elements *and* relations. Adding a relation between two existing components
is one of the commonest real architecture changes, and counting only elements made that case render
`0 added, 0 removed, 0 changed` above a populated relationships section.

### A relation is keyed by its endpoints' pairing, not by its own derived identifier

A relation's `destinationId` is derived from the target's name, so renaming one element would change
every relation pointing at it. Resolving both endpoints through the element pairing first means a
rename produces one line instead of N false relation changes — on this project's own graph, renaming
the Backend container would otherwise have produced about ten.

### The changed-file set is a fact, and it does not propagate

For each element, the comparison can report which of the files it owns changed. That is reported as
data for a visual view to mark, never as an alert: ordinary work touches some element's files on
nearly every commit, so a signal that fires every time carries no information and trains readers to
ignore it.

It is deliberately not propagated along relations. "This element's files changed" is a fact; "the
elements that use it are affected" is an inference about runtime consequence that neither the
annotations nor static analysis prove. The structure enforces this rather than relying on review:
the per-element record has no field in which to name a second element.

Whether a changed-file set means a declaration has become *wrong* stays a human judgement. An
advisory opinion would have to be stored and displayed as plainly inferred rather than authored.

### Publishing runs in the repository being reviewed

The pull-request comment is posted by a job in the reviewed repository under that workflow's own
token, not by the SeeForce GitHub App. The App holds only contents and metadata read access and its
webhook is inactive, so posting would require a new permission that every existing installation
would have to re-approve. Running in the repository needs no SeeForce credential there either.

The comment is output only. When a visual view is built, the backend recomputes the delta from the
two refs with the file-contents access it already has, rather than reading back a rendering.

## Consequences

- A rename is visible as a rename, except inside a file declaring several elements of one kind.
- Moves between parents are still reported as a removal plus an addition; move classification is out
  of scope.
- Baselines gain per-element provenance keys, which rewrites every committed baseline once.
- Nothing in the delta carries a risk level, an impact estimate, or a merge verdict.
