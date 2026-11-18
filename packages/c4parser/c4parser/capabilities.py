"""
@c3:component
name: Capabilities
container: Annotation Parser
technology: Python
description: |
  - Parses a `- ` bullet description into a tree of capabilities
  - Counts the leaves, since a parent bullet only groups its children
  - Diffs two capability trees bullet by bullet:
    - added and removed bullets
    - reworded bullets, paired by text similarity at the same level
short_desc: Turns bullet descriptions into capabilities and diffs them
"""
from difflib import SequenceMatcher

# Below this similarity, a changed bullet reads as one removed and one added.
REWORD_RATIO = 0.6


def parse_capabilities(description: str) -> list[dict]:
    """Return the `- ` bullets of a description as [{"text", "children"}]; prose yields []."""
    roots: list[dict] = []
    stack: list[tuple[int, list[dict]]] = [(-1, roots)]
    for line in description.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("- "):
            if stripped:
                return []
            continue
        indent = len(line) - len(stripped)
        while stack[-1][0] >= indent:
            stack.pop()
        node = {"text": stripped[2:].strip(), "children": []}
        stack[-1][1].append(node)
        stack.append((indent, node["children"]))
    return roots


def count_capabilities(tree: list[dict]) -> int:
    """Count the leaf bullets: a parent only groups the capabilities under it."""
    return sum(count_capabilities(n["children"]) if n["children"] else 1 for n in tree)


def _mark(tree: list[dict], status: str) -> list[dict]:
    return [{"text": n["text"], "status": status, "children": _mark(n["children"], status)} for n in tree]


def _similarity(a: str, b: str) -> float:
    """Text similarity, where a bullet extended or trimmed in place counts as a full match."""
    a, b = a.lower(), b.lower()
    if a in b or b in a:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def diff_capability_trees(before: list[dict], after: list[dict]) -> list[dict]:
    """Merge two trees into one whose nodes carry status unchanged/added/removed/reworded."""
    by_text = {n["text"]: n for n in before}
    matched: dict[int, dict] = {i: by_text.pop(n["text"]) for i, n in enumerate(after) if n["text"] in by_text}
    leftover = [n for n in before if n["text"] in by_text]
    for i, n in enumerate(after):
        if i in matched or not leftover:
            continue
        best = max(leftover, key=lambda b: _similarity(b["text"], n["text"]))
        if _similarity(best["text"], n["text"]) >= REWORD_RATIO:
            matched[i] = best
            leftover.remove(best)

    merged: dict[int, dict] = {}
    for i, n in enumerate(after):
        old = matched.get(i)
        if old is None:
            merged[i] = _mark([n], "added")[0]
            continue
        merged[i] = {
            "text": n["text"],
            "status": "unchanged" if old["text"] == n["text"] else "reworded",
            "children": diff_capability_trees(old["children"], n["children"]),
        }
        if merged[i]["status"] == "reworded":
            merged[i]["before"] = old["text"]

    # A removed bullet sits right after the bullet that preceded it in the old list.
    after_index = {id(old): i for i, old in matched.items()}
    out = [merged[i] for i in range(len(after))]
    gone = {id(n) for n in leftover}
    anchor_pos = -1
    for old in before:
        if id(old) in after_index:
            anchor = merged[after_index[id(old)]]
            anchor_pos = next(k for k, n in enumerate(out) if n is anchor)
        elif id(old) in gone:
            anchor_pos += 1
            out.insert(anchor_pos, _mark([old], "removed")[0])
    return out


def diff_capabilities(before: str, after: str) -> list[dict]:
    """Diff two bullet descriptions; an edge's single phrase counts as one bullet."""
    return diff_capability_trees(_as_tree(before), _as_tree(after))


def _as_tree(text: str) -> list[dict]:
    text = text.strip()
    if not text:
        return []
    return parse_capabilities(text) or [{"text": text, "children": []}]


def changed_capabilities(tree: list[dict]) -> list[tuple[str, str, str]]:
    """Flatten a merged tree into (status, text, before) for every leaf or parent that changed."""
    rows: list[tuple[str, str, str]] = []
    for n in tree:
        if n["status"] != "unchanged":
            rows.append((n["status"], n["text"], n.get("before", "")))
        if n["status"] in ("unchanged", "reworded"):
            rows += changed_capabilities(n["children"])
    return rows
