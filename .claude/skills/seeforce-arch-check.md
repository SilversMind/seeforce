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

3. **Analyze each file's result**:
   - `annotation present: yes` + confidence `exact` → no action needed
   - `annotation present: no` + wrong container inferred → new component or container candidate
   - New external dependency visible in code but not in any `uses:` edge → missing `@c1:external`
   - New cross-container call not reflected in existing edges → missing `uses:` entry

4. **For each gap found**, propose the specific annotation change:
   - New component: show the `@c3:component` block to add at top of the file
   - New container: show the `@c2:container` block
   - New external: show the `@c1:external` block + which `uses:` entry to add
   - New edge only: show the `uses:` entry to append to an existing annotation

5. **Ask the user** which proposals to apply.

6. **After applying**, run `seeforce scan .` to regenerate and validate workspace.json, then call `mcp__seeforce__get_context` to confirm the change is visible.

## Rules

- Never annotate config files (settings, pyproject.toml/package.json, .env, CI config).
- Never annotate test files.
- Never annotate migration files.
- A new file that fits an existing component's responsibility does NOT need its own annotation — only add one if it introduces a distinct named concern.
- Use `mcp__seeforce__get_context` output as the source of truth for what already exists; do not rely on memory.
