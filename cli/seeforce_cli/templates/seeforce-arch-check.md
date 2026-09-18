---
name: seeforce-arch-check
description: After implementing a feature or fix in this codebase, check whether the changed files justify architecture annotation updates using the SeeForce MCP server.
triggers:
  - after implementing a feature, fix, or refactor that touches source files
  - when the user asks to check architecture or annotations
---

## When to invoke

A Stop hook (`.claude/hooks/arch-sync-check.sh`) runs automatically at the end of every turn and does a cheap, no-LLM heuristic pre-filter on uncommitted source files (new file, new import, new class/function/component, new route). When it finds a match, it injects a reminder into context — **invoke this skill when that reminder appears**, before considering the task done.

The hook is deliberately dumb (regex/diff-stat only, same de-dup per unchanged diff so it doesn't nag every turn) — it can't tell whether a change is *semantically* significant, only whether it *looks* structurally significant. This skill is where the actual judgment happens: comparing current annotations against what the code now does.

You can also invoke it manually — e.g. after a session that predates this hook, after hand-edited code the hook never saw, or when the user asks to check architecture directly.

Do NOT invoke for: pure UI styling, test-only changes, config tweaks with no new responsibilities — same exclusion list as `CLAUDE.md`'s "before any important change" rule.

## Steps

1. **Collect modified files** from the session (files edited or created).

2. **Call `mcp__seeforce__get_architecture_for_files`** with those file paths.

   **If the call errors:** stop and report the failure to the user as a failed check — do not fall back to a manual/from-memory review and report it as if it were equivalent. A silently-degraded check that still says "no gaps found" is worse than no check at all. (As of 2026-09, tool errors return a diagnosable message — e.g. which backend URL/token was used and which file the MCP server actually ran from — instead of an opaque failure; read it, it usually says exactly what's misconfigured.)

3. **Call `mcp__seeforce__get_static_facts_for_files`** with the same file paths. This re-derives the import graph from the file's current content — it catches edges the annotations claim (or omit) regardless of *how* the code got there, including refactors that changed a call site without adding any new import/class/def line the Stop hook's regex would notice. Same error-handling rule as step 2 applies here too.

4. **Reconcile the two**:
   - `annotation present: yes` + confidence `exact` + no unresolved static-facts candidate for that file → no action needed
   - `annotation present: no` + wrong container inferred → new component or container candidate
   - New external dependency visible in code but not in any `uses:` edge → missing `@c1:external`
   - New cross-container call not reflected in existing edges → missing `uses:` entry
   - A static-facts candidate edge whose `to_component` is a known component **not** present in that container's `uses:` list → possible missing edge. Static facts is import-only recall, not verified truth (see the tool's own caveat) — confirm there's a real call site before proposing it, same bar as any other gap here.
   - An existing `uses:` edge with **no** corresponding static-facts candidate for that file → possible stale edge from a deleted/rewired call. Confirm the code truly no longer does this (static facts can't see dynamic wiring — DI, reflection, config-driven routes, message-bus subscriptions — so absence alone isn't proof) before proposing removal.

5. **For each gap found**, propose the specific annotation change:
   - New component: show the `@c3:component` block to add at top of the file
   - New container: show the `@c2:container` block
   - New external: show the `@c1:external` block + which `uses:` entry to add
   - New edge only: show the `uses:` entry to append to an existing annotation
   - Stale edge: show which `uses:` entry to remove and why

6. **Ask the user** which proposals to apply.

7. **After applying**, run `seeforce scan .` to regenerate and validate workspace.json, then call `mcp__seeforce__get_context` to confirm the change is visible.

## Rules

- Never annotate config files (settings, pyproject.toml/package.json, .env, CI config).
- Never annotate test files.
- Never annotate migration files.
- A new file that fits an existing component's responsibility does NOT need its own annotation — only add one if it introduces a distinct named concern.
- Use `mcp__seeforce__get_context` output as the source of truth for what already exists; do not rely on memory.
