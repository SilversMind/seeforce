import os
import re
import textwrap
import yaml
from pathlib import Path

from .types import C4System, C4Container, C4Component, C4Element
from .exceptions import C4ParseError

_BLOCK_RE = re.compile(
    r'(?:"""|\'\'\')(.*?)(?:"""|\'\'\')',
    re.DOTALL,
)
_PREFIX_RE = re.compile(r"@c([123]):(\w+)")

_DEFAULT_EXTENSIONS = {".py", ".java", ".ts", ".tsx", ".js", ".go", ".cs", ".rb"}
_DEFAULT_EXCLUDES = {
    "node_modules", "__pycache__", ".git", "dist", "build", "vendor",
    ".venv", "venv", ".env",
}


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _parse_block(content: str, file_path: str) -> C4Element | None:
    match = _PREFIX_RE.search(content)
    if not match:
        return None

    level, kind = match.group(1), match.group(2)
    # Remove the @cN:kind line before parsing YAML, then dedent
    yaml_text = _PREFIX_RE.sub("", content, count=1)
    yaml_text = textwrap.dedent(yaml_text).strip()

    try:
        data = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        raise C4ParseError(str(exc), file_path=file_path)

    if not isinstance(data, dict):
        return None

    data["source_file"] = file_path

    match level:
        case "1":
            if "name" not in data:
                raise C4ParseError("@c1:system missing required field 'name'", file_path)
            return C4System(**{k: v for k, v in data.items() if k in C4System.__dataclass_fields__})
        case "2":
            for req in ("name", "system"):
                if req not in data:
                    raise C4ParseError(f"@c2:container missing required field '{req}'", file_path)
            return C4Container(**{k: v for k, v in data.items() if k in C4Container.__dataclass_fields__})
        case "3":
            for req in ("name", "container"):
                if req not in data:
                    raise C4ParseError(f"@c3:component missing required field '{req}'", file_path)
            return C4Component(**{k: v for k, v in data.items() if k in C4Component.__dataclass_fields__})
    return None


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

            for match in _BLOCK_RE.finditer(text):
                block = match.group(1)
                if "@c" not in block:
                    continue
                element = _parse_block(block, file_path)
                if element is not None:
                    elements.append(element)

    return elements
