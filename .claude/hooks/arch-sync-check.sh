#!/bin/bash
# Stop hook: cheap heuristic pre-filter for architecture drift.
# Looks only at currently uncommitted changes to significant source files.
# If the diff looks structurally significant (new file, or an import,
# class/function/component definition or route added OR removed), injects a
# reminder to run
# the seeforce-arch-check skill before finishing. Otherwise stays silent.
set -eu

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$ROOT" || exit 0

RAW_STATUS="$(git status --porcelain=v1 2>/dev/null)"
[ -z "$RAW_STATUS" ] && exit 0

CHANGED="$(printf '%s\n' "$RAW_STATUS" | cut -c4-)"

# Significant source extensions only, excluding tests/migrations/config/vendor
# per this repo's own CLAUDE.md exclusion list.
FILTERED="$(printf '%s\n' "$CHANGED" | grep -E '\.(py|tsx?|jsx?)$' | grep -vE '(/tests?/|/migrations/|/settings/|\.venv/|node_modules/|/dist/|/build/|(^|/)test_[^/]*\.py$|\.test\.tsx?$)' || true)"
[ -z "$FILTERED" ] && exit 0

FILES=()
while IFS= read -r line; do
  [ -n "$line" ] && FILES+=("$line")
done <<< "$FILTERED"

# Untracked/newly-added files never show content via `git diff` — split them
# out and read their content directly instead.
NEW_FILES=()
MODIFIED_FILES=()
for f in "${FILES[@]}"; do
  if printf '%s\n' "$RAW_STATUS" | grep -qxF "?? $f" || printf '%s\n' "$RAW_STATUS" | grep -qxF "A  $f"; then
    NEW_FILES+=("$f")
  else
    MODIFIED_FILES+=("$f")
  fi
done

DIFF=""
if [ "${#MODIFIED_FILES[@]}" -gt 0 ]; then
  DIFF="$(git diff HEAD -- "${MODIFIED_FILES[@]}" 2>/dev/null)"
fi
NEW_CONTENT=""
if [ "${#NEW_FILES[@]}" -gt 0 ]; then
  NEW_CONTENT="$(cat "${NEW_FILES[@]}" 2>/dev/null | sed 's/^/+/')"
fi
COMBINED="$DIFF
$NEW_CONTENT"

HASH_FILE=".git/.arch-sync-check-hash"
CURRENT_HASH="$(printf '%s' "$COMBINED" | shasum -a 256 | cut -d' ' -f1)"
if [ -f "$HASH_FILE" ] && [ "$(cat "$HASH_FILE" 2>/dev/null)" = "$CURRENT_HASH" ]; then
  exit 0
fi

SIGNIFICANT=0
[ "${#NEW_FILES[@]}" -gt 0 ] && SIGNIFICANT=1 || true
printf '%s' "$COMBINED" | grep -qE '^[+-]\s*(import |from .+ import|require\(|export \{)' && SIGNIFICANT=1 || true
printf '%s' "$COMBINED" | grep -qE '^[+-]\s*(class |def |function |export function|export class|export default function)' && SIGNIFICANT=1 || true
printf '%s' "$COMBINED" | grep -qE '^[+-].*(path\(|router\.register\(|@api_view|urlpatterns|app\.(get|post|put|delete)\()' && SIGNIFICANT=1 || true

if [ "$SIGNIFICANT" = "1" ]; then
  echo "$CURRENT_HASH" > "$HASH_FILE"
  FILES_LIST="$(printf '%s, ' "${FILES[@]}")"
  MSG="Architecture sync check: uncommitted changes to ${FILES_LIST%, } look structurally significant (new file, import, class/function definition, or route). Before finishing this task, invoke the seeforce-arch-check skill to verify C4 annotations are still in sync with the code, per this repo's CLAUDE.md."
  python3 -c "import json,sys; print(json.dumps({'hookSpecificOutput': {'hookEventName': 'Stop', 'additionalContext': sys.argv[1]}}))" "$MSG"
fi
exit 0
