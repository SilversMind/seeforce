<!-- seeforce:arch-sync-section -->
## Keeping C4 architecture annotations in sync

### Before any important change

Before implementing a significant feature, new service, new module, or architectural shift, ask:

> "Does this change deserve to be documented in the C4 annotations (new Container, Component, or relation) so the architecture stays accurate?"

If yes, propose the C4 elements to add or update before writing code.

**Counts as "important":**
- New service or app (C4 Container)
- New distinct functional module (C4 Component)
- New external dependency (database, third-party API, auth provider)
- Change in communication protocol between components
- New boundary (bounded context, network zone, domain)

**Does NOT need a C4 update:**
- Bugfixes
- Internal refactoring within a component
- Cosmetic UI changes
- Adding fields to an existing model

### After a change — check for drift

A Stop hook (`.claude/hooks/arch-sync-check.sh`) runs automatically at the end of each turn. It looks only at uncommitted source files and checks for cheap structural signals (new file, new import, new class/function/component, new route) — no LLM, so it stays silent on bugfixes and trivial changes. The same diff is only flagged once, not re-nagged every turn.

When it detects a potentially significant change, it injects a reminder into context. **If that reminder appears, invoke the `seeforce-arch-check` skill before considering the task done** — it compares the current C4 annotation state (via `mcp__seeforce__get_architecture_for_files`) against what the code actually does, and proposes the necessary fixes.

The hook is a deliberately simple heuristic pass (no semantic judgment) — it doesn't replace the "before any important change" question above, it catches what slips through it.
