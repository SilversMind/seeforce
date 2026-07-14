import os
import re
import textwrap
import yaml
from pathlib import Path

from .types import C4System, C4Container, C4Component, C4Element
from .exceptions import C4ParseError

# Triple-quoted Python docstrings — backreference so quotes must match.
_PY_BLOCK_RE = re.compile(r'(?P<q>"""|\'\'\')(.*?)(?P=q)', re.DOTALL)
# C-style block comments: /* ... */ and /** ... */ (Java, TS, Go, C#, JS).
_C_BLOCK_RE = re.compile(r"/\*+(.*?)\*/", re.DOTALL)

_PREFIX_RE = re.compile(r"@c([123]):(\w+)")

_EXPECTED_KIND = {"1": "system", "2": "container", "3": "component"}

_DEFAULT_EXTENSIONS = {".py", ".java", ".ts", ".tsx", ".js", ".go", ".cs", ".rb"}
_DEFAULT_EXCLUDES = {
    "node_modules", "__pycache__", ".git", "dist", "build", "vendor",
    ".venv", "venv", ".env",
}


def _strip_comment_stars(block: str) -> str:
    # Javadoc-style blocks prefix each line with " * " — strip it.
    lines = [re.sub(r"^\s*\*\s?", "", line) for line in block.splitlines()]
    return "\n".join(lines)


def _parse_block(content: str, file_path: str, line: int) -> C4Element | None:
    # An annotation block must START with the @cN: marker (after dedent).
    # Anything else is code that merely mentions "@cN:" in a string literal —
    # skipping it prevents the scanner from tripping on its own source.
    stripped = textwrap.dedent(content).strip()
    if not stripped.startswith("@c"):
        return None

    match = _PREFIX_RE.match(stripped)
    if not match:
        return None

    level, kind = match.group(1), match.group(2)
    expected = _EXPECTED_KIND[level]
    if kind != expected:
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

    data["source_file"] = file_path

    match level:
        case "1":
            if "name" not in data:
                raise C4ParseError("@c1:system missing required field 'name'", file_path, line)
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


def scan(
    root_path: str,
    extensions: list[str] | None = None,
    excludes: set[str] | None = None,
) -> list[C4Element]:
    exts = set(extensions) if extensions else _DEFAULT_EXTENSIONS
    excl = excludes if excludes is not None else _DEFAULT_EXCLUDES
    elements: list[C4Element] = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune excluded dirs in-place so os.walk skips them
        dirnames[:] = [d for d in dirnames if d not in excl]

        for filename in filenames:
            if Path(filename).suffix not in exts:
                continue
            file_path = os.path.join(dirpath, filename)
            try:
                text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            if "@c" not in text:
                continue  # fast path

            for block, line in _extract_blocks(text):
                if "@c" not in block:
                    continue
                element = _parse_block(block, file_path, line)
                if element is not None:
                    elements.append(element)

    return elements
