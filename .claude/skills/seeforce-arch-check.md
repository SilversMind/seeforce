---
name: seeforce-arch-check
description: After implementing a feature or fix in the SeeForce codebase, check whether the changed files justify architecture annotation updates using the SeeForce MCP server.
triggers:
  - after implementing a feature, fix, or refactor that touches backend or frontend source files
  - when the user asks to check architecture or annotations
---

## When to invoke

Invoke this skill automatically after any implementation session that:
- Creates a new file
- Adds a new route, endpoint, service, or consumer
- Introduces a new external dependency (package, API, protocol)
- Changes how containers communicate

Do NOT invoke for: pure UI styling, test-only changes, config tweaks with no new responsibilities.

## Steps

1. **Collect modified files** from the session (files edited or created).

2. **Call `mcp__seeforce__get_architecture_for_files`** with those file paths.

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

6. **After applying**, run `just scan` to push updated workspace to backend, then call `mcp__seeforce__get_context` to confirm the change is visible.

## Rules

- Never annotate config files (settings.py, pyproject.toml, .env, Justfile).
- Never annotate test files.
- Never annotate migration files.
- A new file that fits an existing component's responsibility does NOT need its own annotation — only add one if it introduces a distinct named concern.
- Use `mcp__seeforce__get_context` output as the source of truth for what already exists; do not rely on memory.
