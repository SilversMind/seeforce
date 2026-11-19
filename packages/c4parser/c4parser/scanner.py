"""
@c3:component
name: Annotation Scanner
container: Annotation Parser
description: |
  - Walks a repo's source files
  - Parses @c1/@c2/@c3/@lexicon blocks from comments and docstrings into a flat element list
  - Normalizes descriptions into `- ` bullet text
  - Counts the non-blank lines of every source file it walks
short_desc: Walks source files and extracts @c1/@c2/@c3/@lexicon blocks
"""
import fnmatch
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml

from .exceptions import C4ParseError
from .types import C4Component, C4Container, C4Element, C4Lexicon, C4Person, C4System

# Triple-quoted Python docstrings — backreference so quotes must match.
_PY_BLOCK_RE = re.compile(r'(?P<q>"""|\'\'\')(.*?)(?P=q)', re.DOTALL)
# C-style block comments: /* ... */ and /** ... */ (Java, TS, Go, C#, JS).
_C_BLOCK_RE = re.compile(r"/\*+(.*?)\*/", re.DOTALL)

_PREFIX_RE = re.compile(r"@c([123]):(\w+)")

_EXPECTED_KIND = {"1": "system", "2": "container", "3": "component"}
_VALID_KINDS = {"1": {"system", "person", "external"}, "2": {"container"}, "3": {"component"}}

_DEFAULT_EXTENSIONS = {".py", ".java", ".ts", ".tsx", ".js", ".mjs", ".go", ".cs", ".rb", ".rs"}
DEFAULT_EXTENSIONS = _DEFAULT_EXTENSIONS
_DEFAULT_EXCLUDES = {
    "node_modules", "__pycache__", ".git", "dist", "build", "vendor",
    ".venv", "venv", ".env", "tests", ".claude",
}


def _load_c4ignore(root_path: str) -> list[str]:
    """Return patterns from .seeforce/.c4ignore or .c4ignore at root_path."""
    root = Path(root_path)
    for candidate in (root / ".seeforce" / ".c4ignore", root / ".c4ignore"):
        if candidate.exists():
            patterns = []
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip().rstrip("/")
                if line and not line.startswith("#"):
                    patterns.append(line)
            return patterns
    return []


def _is_ignored(name: str, patterns: list[str], rel_path: str = "") -> bool:
    # Always match against the relative path from root — no "anywhere in tree"
    # magic. `examples` only excludes the root-level examples/, not sub/examples/.
    target = rel_path if rel_path else name
    return any(fnmatch.fnmatch(target, p) for p in patterns)


def _strip_comment_stars(block: str) -> str:
    # Javadoc-style blocks prefix each line with " * " — strip it.
    lines = [re.sub(r"^\s*\*\s?", "", line) for line in block.splitlines()]
    return "\n".join(lines)


def _bullet_lines(value: object, depth: int) -> list[str]:
    indent = "  " * depth
    if isinstance(value, list):
        return [line for item in value for line in _bullet_lines(item, depth)]
    if isinstance(value, dict):
        lines: list[str] = []
        for head, children in value.items():
            lines.append(f"{indent}- {head}:" if children else f"{indent}- {head}")
            if children:
                lines.extend(_bullet_lines(children, depth + 1))
        return lines
    return [f"{indent}- {str(value).strip()}"]


def format_description(value: object) -> str:
    """Returns a description as text, turning a YAML list (nested via `item:` keys) into `- ` bullet lines."""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return "\n".join(_bullet_lines(value, 0))
    return "\n".join(line.rstrip() for line in textwrap.dedent(str(value)).strip().splitlines())


def _parse_block(content: str, file_path: str, line: int, git_root: str | None = None) -> C4Element | None:
    # The @cN: / @lexicon marker must START a line (after dedent) — summary
    # lines before it are allowed, but mid-line mentions in string literals
    # are not, so the scanner never trips on its own error messages.
    stripped = textwrap.dedent(content).strip()
    lex_marker = re.search(r"(?m)^@lexicon\b", stripped)
    c_marker = re.search(r"(?m)^@c[123]:", stripped)
    if lex_marker and (not c_marker or lex_marker.start() < c_marker.start()):
        return _parse_lexicon_block(stripped[lex_marker.end():], file_path, line, git_root)
    marker = c_marker
    if not marker:
        return None

    stripped = stripped[marker.start():]
    match = _PREFIX_RE.match(stripped)
    if not match:
        return None

    level, kind = match.group(1), match.group(2)
    if kind not in _VALID_KINDS[level]:
        expected = _EXPECTED_KIND[level]
        raise C4ParseError(
            f"@c{level}:{kind} is invalid — level {level} must be @c{level}:{expected}",
            file_path=file_path,
            line=line,
        )

    # Remove the @cN:kind marker line; the rest is the YAML payload
    yaml_text = stripped[match.end():].strip()

    try:
        data = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        raise C4ParseError(str(exc), file_path=file_path, line=line)

    if not isinstance(data, dict):
        return None

    ref_root = git_root if git_root else os.path.dirname(file_path)
    data["source_file"] = os.path.relpath(file_path, ref_root).replace(os.sep, "/")
    if "description" in data:
        data["description"] = format_description(data["description"])

    match level:
        case "1":
            if "name" not in data:
                raise C4ParseError(f"@c1:{kind} missing required field 'name'", file_path, line)
            if kind == "person":
                return C4Person(**{k: v for k, v in data.items() if k in C4Person.__dataclass_fields__})
            if kind == "external":
                data["external"] = True
            return C4System(**{k: v for k, v in data.items() if k in C4System.__dataclass_fields__})
        case "2":
            for req in ("name", "system"):
                if req not in data:
                    raise C4ParseError(f"@c2:container missing required field '{req}'", file_path, line)
            return C4Container(**{k: v for k, v in data.items() if k in C4Container.__dataclass_fields__})
        case "3":
            for req in ("name", "container"):
                if req not in data:
                    raise C4ParseError(f"@c3:component missing required field '{req}'", file_path, line)
            return C4Component(**{k: v for k, v in data.items() if k in C4Component.__dataclass_fields__})
    return None


def _parse_lexicon_block(rest: str, file_path: str, line: int, git_root: str | None) -> C4Lexicon | None:
    yaml_text = rest.strip()
    try:
        data = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        raise C4ParseError(str(exc), file_path=file_path, line=line)
    if not isinstance(data, dict):
        return None
    for req in ("term", "definition"):
        if req not in data:
            raise C4ParseError(f"@lexicon missing required field '{req}'", file_path, line)
    ref_root = git_root if git_root else os.path.dirname(file_path)
    data["source_file"] = os.path.relpath(file_path, ref_root).replace(os.sep, "/")
    return C4Lexicon(**{k: v for k, v in data.items() if k in C4Lexicon.__dataclass_fields__})


def _extract_blocks(text: str) -> list[tuple[str, int]]:
    """Return (block_content, line_number) pairs from all comment styles."""
    blocks: list[tuple[str, int]] = []
    for match in _PY_BLOCK_RE.finditer(text):
        line = text[: match.start()].count("\n") + 1
        blocks.append((match.group(2), line))
    for match in _C_BLOCK_RE.finditer(text):
        line = text[: match.start()].count("\n") + 1
        blocks.append((_strip_comment_stars(match.group(1)), line))
    return blocks


def _source_files(root_path: str, exts: set[str], excl: set[str]):
    """Yields (dirpath, file_path, text) for every source file under root_path, in tree order."""
    ignore = _load_c4ignore(root_path)
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune excluded dirs in-place so os.walk skips them.
        # rel_path uses forward slashes for cross-platform pattern matching.
        pruned = []
        for d in dirnames:
            if d in excl:
                continue
            rel_d = os.path.relpath(os.path.join(dirpath, d), root_path).replace(os.sep, "/")
            if _is_ignored(d, ignore, rel_path=rel_d):
                continue
            pruned.append(d)
        # Sorted so the walk order is the tree's, not the filesystem's — an unsorted
        # NOTE: walk puts elements in a different order on ext4 than on APFS, which breaks the byte-identical rescan.
        dirnames[:] = sorted(pruned)

        for filename in sorted(filenames):
            if Path(filename).suffix not in exts:
                continue
            rel_f = os.path.relpath(os.path.join(dirpath, filename), root_path).replace(os.sep, "/")
            if _is_ignored(filename, ignore, rel_path=rel_f):
                continue
            file_path = os.path.join(dirpath, filename)
            try:
                text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            yield dirpath, file_path, text


class _GitRoots:
    """Caches `git rev-parse --show-toplevel` per directory."""

    def __init__(self) -> None:
        self._cache: dict[str, str | None] = {}

    def __call__(self, dirpath: str) -> str | None:
        if dirpath not in self._cache:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=dirpath, capture_output=True, text=True, timeout=5, check=False,
                )
                self._cache[dirpath] = result.stdout.strip() if result.returncode == 0 else None
            except Exception:
                self._cache[dirpath] = None
        return self._cache[dirpath]


def scan(
    root_path: str,
    extensions: list[str] | None = None,
    excludes: set[str] | None = None,
) -> list[C4Element]:
    exts = set(extensions) if extensions else _DEFAULT_EXTENSIONS
    excl = excludes if excludes is not None else _DEFAULT_EXCLUDES
    elements: list[C4Element] = []
    # Per-directory, not once for root_path: root_path may be a shared parent of several repos.
    # NOTE: a single root-level lookup would degrade every source_file to a bare filename and break ownership inference.
    git_root_for = _GitRoots()

    for dirpath, file_path, text in _source_files(root_path, exts, excl):
        if "@c" not in text and "@lexicon" not in text:
            continue  # fast path

        for block, line in _extract_blocks(text):
            if "@c" not in block and "@lexicon" not in block:
                continue
            try:
                element = _parse_block(block, file_path, line, git_root=git_root_for(dirpath))
            except C4ParseError as exc:
                print(f"Warning: {exc}", file=sys.stderr)
                continue
            if element is not None:
                elements.append(element)

    return elements


def count_lines(
    root_path: str,
    extensions: list[str] | None = None,
    excludes: set[str] | None = None,
) -> dict[str, int]:
    """Returns the non-blank line count of every scanned source file, keyed like source_file."""
    exts = set(extensions) if extensions else _DEFAULT_EXTENSIONS
    excl = excludes if excludes is not None else _DEFAULT_EXCLUDES
    git_root_for = _GitRoots()
    counts: dict[str, int] = {}
    for dirpath, file_path, text in _source_files(root_path, exts, excl):
        ref_root = git_root_for(dirpath) or os.path.dirname(file_path)
        rel = os.path.relpath(file_path, ref_root).replace(os.sep, "/")
        counts[rel] = sum(1 for line in text.splitlines() if line.strip())
    return counts
