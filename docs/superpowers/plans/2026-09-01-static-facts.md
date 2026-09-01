# Static Facts (tree-sitter) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the C4 annotator LLM and the `seeforce-arch-check` drift flow a statically-extracted, clearly-labeled-as-candidate import graph (Python + TypeScript, via tree-sitter) as a recall aid — never a source of truth.

**Architecture:** An isolated `static_facts/` subpackage inside `packages/c4parser/c4parser/` does per-file extraction (tree-sitter) → heuristic import resolution → noise filtering, behind one public function `extract_facts()`. A new small module in `mcp/` and its `cli/seeforce_cli/` twin collapses the resulting file-level edges to component-level candidates by reusing the existing `infer_owner()` file→component lookup, then exposes it as a new MCP tool.

**Tech Stack:** Python 3.11+, `tree-sitter` + `tree-sitter-language-pack` (optional extra), `pytest`, `uv` (dependency management for `packages/c4parser` and `cli`).

**Spec:** `docs/superpowers/specs/2026-09-01-static-facts-design.md`

## Global Constraints

- Languages v1: **Python and TypeScript only** (spec Scope).
- `static_facts/` is the only place that imports tree-sitter — nothing outside it imports `backend.py`/`resolver.py` directly (spec Architecture — isolation rule).
- `tree-sitter` + `tree-sitter-language-pack` are an **optional** dependency (`static-facts` extra) — base `c4parser` install must not require them (spec Architecture — optional dependency).
- No persisted cache, no new CLI command — facts are computed on demand per MCP call over the requested files only (spec Non-goals).
- Cross-component collapsing reuses the existing `infer_owner()` in `mcp/ownership.py` / `mcp_ownership.py` — do not build a new file→component lookup (spec Architecture).
- The same filter code path handles both cold-start (empty `workspace.json`) and re-scan (populated) — no separate "bootstrap mode" branch (spec Non-goals).
- New MCP tool lands in **both** `mcp/server.py` (repo dogfooding) and `cli/seeforce_cli/mcp_server.py` (shipped package) — see spec's MCP exposure correction.
- Prompt edit targets **only** `cli/seeforce_cli/prompts/c4_annotator.md` (canonical, runtime-used copy) — never the stale root `prompts/c4_annotator.md`.
- `backend/c4parser/` (vendored copy) is **not** touched by this plan.

---

## Task 1: Package scaffold — types, degrade guard, dependency wiring

**Files:**
- Create: `packages/c4parser/c4parser/static_facts/__init__.py`
- Create: `packages/c4parser/c4parser/static_facts/types.py`
- Modify: `packages/c4parser/pyproject.toml`
- Create: `packages/c4parser/tests/__init__.py`
- Create: `packages/c4parser/tests/static_facts/__init__.py`
- Test: `packages/c4parser/tests/static_facts/test_init.py`

**Interfaces:**
- Produces: `FileFacts(file: str, imports: list[ImportFact], defines: list[DefFact])`, `ImportFact(raw: str, resolved_path: str | None, kind: str)`, `DefFact(name: str, kind: str, docstring: str)` — all in `static_facts.types`, all later tasks import from here.
- Produces: `extract_facts(root: str, files: list[str]) -> list[FileFacts]` in `static_facts` (public entrypoint; body is a stub returning `[]` in this task, filled in by Task 6).
- Produces: `_backend_available() -> bool` in `static_facts` — module-level, monkeypatchable.

- [ ] **Step 1: Write the failing test**

```python
# packages/c4parser/tests/static_facts/test_init.py
import c4parser.static_facts as sf


def test_extract_facts_degrades_without_backend(monkeypatch):
    monkeypatch.setattr(sf, "_backend_available", lambda: False)
    assert sf.extract_facts(".", ["whatever.py"]) == []


def test_extract_facts_empty_file_list():
    assert sf.extract_facts(".", []) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/test_init.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'c4parser.static_facts'` (package doesn't exist yet).

- [ ] **Step 3: Write `types.py`**

```python
# packages/c4parser/c4parser/static_facts/types.py
from dataclasses import dataclass, field


@dataclass
class ImportFact:
    raw: str
    resolved_path: str | None = None
    kind: str = "internal"  # "internal" | "external_known"


@dataclass
class DefFact:
    name: str
    kind: str  # "function" | "class"
    docstring: str = ""


@dataclass
class FileFacts:
    file: str
    imports: list[ImportFact] = field(default_factory=list)
    defines: list[DefFact] = field(default_factory=list)
```

- [ ] **Step 4: Write `__init__.py` (stub `extract_facts`)**

```python
# packages/c4parser/c4parser/static_facts/__init__.py
"""
@c3:component
name: Static Facts Extractor
container: Annotation Parser
technology: tree-sitter
description: Statically extracts imports, top-level definitions, and adjacent docstrings from source files (Python, TypeScript) as an unverified candidate signal — never a source of truth. Isolated in its own subpackage behind extract_facts() so tree-sitter (an optional dependency) can be dropped without breaking annotation scanning or building.
"""
import importlib.util

from .types import DefFact, FileFacts, ImportFact

__all__ = ["extract_facts", "FileFacts", "ImportFact", "DefFact"]


def _backend_available() -> bool:
    return importlib.util.find_spec("tree_sitter_language_pack") is not None


def extract_facts(root: str, files: list[str]) -> list[FileFacts]:
    """
    Given a repo root and a list of file paths, return statically-extracted
    candidate facts for each recognized (Python/TypeScript) file. Returns []
    if the optional `static-facts` extra isn't installed, or if `files` is
    empty. Never raises on a per-file parse error — that file is skipped.
    """
    if not _backend_available() or not files:
        return []
    return []  # filled in by Task 6
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/test_init.py -v`
Expected: PASS (both tests — `extract_facts` returns `[]` unconditionally at this stage, which satisfies both).

- [ ] **Step 6: Add the optional dependency and dev group to `pyproject.toml`**

```toml
[project.optional-dependencies]
static-facts = ["tree-sitter>=0.23", "tree-sitter-language-pack>=0.24"]
dev = ["pytest>=8.0"]
```

Run: `cd packages/c4parser && uv add --optional static-facts tree-sitter tree-sitter-language-pack && uv add --optional dev pytest`
(If `uv add --optional` errors on this uv version, edit `pyproject.toml` by hand as above, then run `uv sync --extra static-facts --extra dev`.)

- [ ] **Step 7: Sync and re-run full test suite**

Run: `cd packages/c4parser && uv sync --extra static-facts --extra dev && uv run pytest tests/ -v`
Expected: PASS, all tests green, `tree_sitter_language_pack` now installed in `.venv`.

- [ ] **Step 8: Commit**

```bash
git add packages/c4parser/pyproject.toml packages/c4parser/uv.lock packages/c4parser/c4parser/static_facts/ packages/c4parser/tests/
git commit -m "feat(c4parser): scaffold static_facts package with degrade guard"
```

---

## Task 2: Noise classification (`noise.py`)

**Files:**
- Create: `packages/c4parser/c4parser/static_facts/noise.py`
- Test: `packages/c4parser/tests/static_facts/test_noise.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `top_level_name(raw: str, language: str) -> str`, `is_known_external(top_name: str, language: str) -> bool`, `is_stdlib(top_name: str, language: str) -> bool` — all consumed by Task 6 (`__init__.py` orchestration).

- [ ] **Step 1: Write the failing tests**

```python
# packages/c4parser/tests/static_facts/test_noise.py
from c4parser.static_facts import noise


def test_top_level_name_python_dotted():
    assert noise.top_level_name("apps.subscriptions.manager", "python") == "apps"


def test_top_level_name_typescript_relative():
    assert noise.top_level_name("./util", "typescript") == "./util"


def test_top_level_name_typescript_bare():
    assert noise.top_level_name("axios/lib/foo", "typescript") == "axios"


def test_top_level_name_typescript_scoped():
    assert noise.top_level_name("@aws-sdk/client-s3", "typescript") == "@aws-sdk/client-s3"


def test_is_known_external_python():
    assert noise.is_known_external("stripe", "python") is True
    assert noise.is_known_external("some_random_lib", "python") is False


def test_is_known_external_typescript():
    assert noise.is_known_external("axios", "typescript") is True
    assert noise.is_known_external("lodash", "typescript") is False


def test_is_stdlib_python():
    assert noise.is_stdlib("os", "python") is True
    assert noise.is_stdlib("stripe", "python") is False


def test_is_stdlib_typescript_node_builtin():
    assert noise.is_stdlib("fs", "typescript") is True
    assert noise.is_stdlib("axios", "typescript") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/test_noise.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'c4parser.static_facts.noise'`.

- [ ] **Step 3: Write `noise.py`**

```python
# packages/c4parser/c4parser/static_facts/noise.py
import sys

# Starting allowlists — extend as real annotation runs surface more.
KNOWN_EXTERNAL_PY = {
    "stripe", "boto3", "redis", "sqlalchemy", "psycopg2", "psycopg",
    "pymongo", "kafka", "celery", "pika", "requests", "httpx",
    "django", "fastapi", "anthropic", "openai",
}

KNOWN_EXTERNAL_TS = {
    "axios", "stripe", "aws-sdk", "pg", "mongoose", "ioredis",
    "amqplib", "kafkajs", "express", "@aws-sdk",
}

_NODE_BUILTINS = {
    "fs", "path", "http", "https", "os", "crypto", "util", "events",
    "stream", "url", "child_process", "net", "querystring", "assert",
}


def top_level_name(raw: str, language: str) -> str:
    """Return the root package/module name an import string refers to."""
    if language == "python":
        return raw.split(".")[0]
    if raw.startswith("."):
        return raw  # relative import — resolver handles it, not a package name
    parts = raw.split("/")
    if raw.startswith("@") and len(parts) >= 2:
        return "/".join(parts[:2])
    return parts[0]


def is_known_external(top_name: str, language: str) -> bool:
    if language == "python":
        return top_name in KNOWN_EXTERNAL_PY
    return top_name in KNOWN_EXTERNAL_TS


def is_stdlib(top_name: str, language: str) -> bool:
    if language == "python":
        return top_name in sys.stdlib_module_names
    return top_name in _NODE_BUILTINS
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/test_noise.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/c4parser/c4parser/static_facts/noise.py packages/c4parser/tests/static_facts/test_noise.py
git commit -m "feat(c4parser): add static-facts noise classification"
```

---

## Task 3: Import resolver (`resolver.py`)

**Files:**
- Create: `packages/c4parser/c4parser/static_facts/resolver.py`
- Test: `packages/c4parser/tests/static_facts/test_resolver.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `detect_package_roots(root: str) -> set[Path]`, `resolve_python_import(raw: str, source_file: str, package_roots: set[Path]) -> str | None`, `resolve_typescript_import(raw: str, source_file: str, package_roots: set[Path]) -> str | None` — all consumed by Task 6.

- [ ] **Step 1: Write the failing tests**

```python
# packages/c4parser/tests/static_facts/test_resolver.py
from pathlib import Path

from c4parser.static_facts import resolver


def test_detect_package_roots_finds_pyproject(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "pyproject.toml").write_text("[project]\nname='x'\n")
    roots = resolver.detect_package_roots(str(tmp_path))
    assert (tmp_path / "pkg").resolve() in roots


def test_detect_package_roots_skips_venv(tmp_path):
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "pyproject.toml").write_text("[project]\nname='x'\n")
    roots = resolver.detect_package_roots(str(tmp_path))
    assert not any(".venv" in str(r) for r in roots)


def test_resolve_python_import_finds_module_file(tmp_path):
    pkg = tmp_path / "apps" / "subscriptions"
    pkg.mkdir(parents=True)
    (pkg / "manager.py").write_text("")
    resolved = resolver.resolve_python_import(
        "apps.subscriptions.manager", str(tmp_path / "caller.py"), {tmp_path}
    )
    assert resolved == str(pkg / "manager.py")


def test_resolve_python_import_finds_package_init(tmp_path):
    pkg = tmp_path / "apps" / "subscriptions"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    resolved = resolver.resolve_python_import(
        "apps.subscriptions", str(tmp_path / "caller.py"), {tmp_path}
    )
    assert resolved == str(pkg / "__init__.py")


def test_resolve_python_import_unresolved_returns_none():
    resolved = resolver.resolve_python_import("nonexistent.module", "caller.py", set())
    assert resolved is None


def test_resolve_typescript_import_relative(tmp_path):
    (tmp_path / "util.ts").write_text("")
    resolved = resolver.resolve_typescript_import(
        "./util", str(tmp_path / "index.ts"), set()
    )
    assert resolved == str(tmp_path / "util.ts")


def test_resolve_typescript_import_bare_specifier_unresolved():
    resolved = resolver.resolve_typescript_import("axios", "index.ts", set())
    assert resolved is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/test_resolver.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'c4parser.static_facts.resolver'`.

- [ ] **Step 3: Write `resolver.py`**

```python
# packages/c4parser/c4parser/static_facts/resolver.py
from pathlib import Path

_SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build"}


def detect_package_roots(root: str) -> set[Path]:
    """Return absolute directories containing pyproject.toml or package.json,
    used to anchor import resolution — skips build/dependency directories."""
    root_path = Path(root).resolve()
    roots: set[Path] = set()
    for marker in ("pyproject.toml", "package.json"):
        for f in root_path.rglob(marker):
            if any(part in _SKIP_DIRS for part in f.parent.parts):
                continue
            roots.add(f.parent.resolve())
    return roots


def resolve_python_import(raw: str, source_file: str, package_roots: set[Path]) -> str | None:
    """raw is a dotted module path, e.g. 'apps.subscriptions.manager'."""
    parts = raw.split(".")
    for pkg_root in package_roots:
        candidate = pkg_root.joinpath(*parts)
        module_file = candidate.with_suffix(".py")
        if module_file.is_file():
            return str(module_file)
        init_file = candidate / "__init__.py"
        if init_file.is_file():
            return str(init_file)
    return None


def resolve_typescript_import(raw: str, source_file: str, package_roots: set[Path]) -> str | None:
    """raw is an import source string with quotes already stripped, e.g.
    './foo' or '../bar/baz'. Bare specifiers (no leading dot) are left
    unresolved in v1 — no node_modules resolution."""
    if not raw.startswith("."):
        return None
    base = (Path(source_file).resolve().parent / raw).resolve()
    candidates = [
        base.with_suffix(".ts"), base.with_suffix(".tsx"), base.with_suffix(".js"),
        base / "index.ts", base / "index.tsx", base / "index.js",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/test_resolver.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/c4parser/c4parser/static_facts/resolver.py packages/c4parser/tests/static_facts/test_resolver.py
git commit -m "feat(c4parser): add static-facts import resolver"
```

---

## Task 4: Python extraction backend

**Files:**
- Create: `packages/c4parser/c4parser/static_facts/backend.py`
- Create: `packages/c4parser/c4parser/static_facts/queries/python.scm`
- Test: `packages/c4parser/tests/static_facts/test_backend_python.py`

**Interfaces:**
- Consumes: `DefFact` from `static_facts.types` (Task 1).
- Produces: `extract_python(file_path: str, source: str) -> tuple[list[str], list[DefFact]]` — consumed by Task 6. `extract_typescript` (Task 5) lives in the same file.

- [ ] **Step 1: Write the failing tests**

```python
# packages/c4parser/tests/static_facts/test_backend_python.py
from c4parser.static_facts.backend import extract_python

SAMPLE = '''
import os
import stripe
from apps.subscriptions import manager


def create_intent(amount):
    """Creates a Stripe payment intent for the given amount."""
    return stripe.PaymentIntent.create(amount=amount)


class PaymentService:
    """Orchestrates payment intent creation and confirmation."""
    pass
'''


def test_extract_python_imports():
    imports, _ = extract_python("sample.py", SAMPLE)
    assert "os" in imports
    assert "stripe" in imports
    assert "apps.subscriptions" in imports


def test_extract_python_defines_function():
    _, defines = extract_python("sample.py", SAMPLE)
    func = next(d for d in defines if d.name == "create_intent")
    assert func.kind == "function"
    assert func.docstring == "Creates a Stripe payment intent for the given amount."


def test_extract_python_defines_class():
    _, defines = extract_python("sample.py", SAMPLE)
    cls = next(d for d in defines if d.name == "PaymentService")
    assert cls.kind == "class"
    assert cls.docstring == "Orchestrates payment intent creation and confirmation."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/test_backend_python.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'c4parser.static_facts.backend'`.

- [ ] **Step 3: Write the query file**

```scheme
; packages/c4parser/c4parser/static_facts/queries/python.scm
(import_statement name: (dotted_name) @import)
(import_statement name: (aliased_import name: (dotted_name) @import))
(import_from_statement module_name: (dotted_name) @import)

(function_definition) @def
(class_definition) @def
```

- [ ] **Step 4: Write `backend.py` (Python half only — TypeScript added in Task 5)**

```python
# packages/c4parser/c4parser/static_facts/backend.py
from pathlib import Path

from tree_sitter_language_pack import get_language, get_parser

from .types import DefFact

_QUERIES_DIR = Path(__file__).parent / "queries"
_PYTHON_QUERY = (_QUERIES_DIR / "python.scm").read_text()


def _node_text(node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")


def _python_docstring(def_node, source_bytes: bytes) -> str:
    body = def_node.child_by_field_name("body")
    if body is None or body.child_count == 0:
        return ""
    first = body.children[0]
    if first.type != "expression_statement" or first.child_count == 0:
        return ""
    string_node = first.children[0]
    if string_node.type != "string":
        return ""
    return _node_text(string_node, source_bytes).strip("\"' \n\t")


def extract_python(file_path: str, source: str) -> tuple[list[str], list[DefFact]]:
    parser = get_parser("python")
    language = get_language("python")
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)

    query = language.query(_PYTHON_QUERY)
    captures = query.captures(tree.root_node)

    imports = [_node_text(n, source_bytes) for n in captures.get("import", [])]

    defines: list[DefFact] = []
    for node in captures.get("def", []):
        name_node = node.child_by_field_name("name")
        name = _node_text(name_node, source_bytes) if name_node else ""
        kind = "class" if node.type == "class_definition" else "function"
        defines.append(DefFact(name=name, kind=kind, docstring=_python_docstring(node, source_bytes)))

    return imports, defines
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/test_backend_python.py -v`
Expected: PASS. If `query.captures()` raises an `AttributeError` or returns a different shape, run `uv run python -c "import tree_sitter; print(tree_sitter.__version__)"` to check the installed binding version and adjust the capture-iteration code to match its actual API (list-of-tuples vs dict-of-lists) — the fixture/assertions stay the same either way.

- [ ] **Step 6: Commit**

```bash
git add packages/c4parser/c4parser/static_facts/backend.py packages/c4parser/c4parser/static_facts/queries/python.scm packages/c4parser/tests/static_facts/test_backend_python.py
git commit -m "feat(c4parser): add tree-sitter Python extraction backend"
```

---

## Task 5: TypeScript extraction backend

**Files:**
- Create: `packages/c4parser/c4parser/static_facts/queries/typescript.scm`
- Modify: `packages/c4parser/c4parser/static_facts/backend.py`
- Test: `packages/c4parser/tests/static_facts/test_backend_typescript.py`

**Interfaces:**
- Consumes: `DefFact`, `_node_text` (Task 4, same file).
- Produces: `extract_typescript(file_path: str, source: str) -> tuple[list[str], list[DefFact]]` — consumed by Task 6.

- [ ] **Step 1: Write the failing tests**

```python
# packages/c4parser/tests/static_facts/test_backend_typescript.py
from c4parser.static_facts.backend import extract_typescript

SAMPLE = '''
import axios from "axios";
import { manager } from "./subscriptions/manager";

/** Creates a Stripe payment intent for the given amount. */
function createIntent(amount) {
  return axios.post("/charge", { amount });
}

/** Orchestrates payment intent creation and confirmation. */
class PaymentService {}
'''


def test_extract_typescript_imports():
    imports, _ = extract_typescript("sample.ts", SAMPLE)
    assert "axios" in imports
    assert "./subscriptions/manager" in imports


def test_extract_typescript_defines_function():
    _, defines = extract_typescript("sample.ts", SAMPLE)
    func = next(d for d in defines if d.name == "createIntent")
    assert func.kind == "function"
    assert func.docstring == "Creates a Stripe payment intent for the given amount."


def test_extract_typescript_defines_class():
    _, defines = extract_typescript("sample.ts", SAMPLE)
    cls = next(d for d in defines if d.name == "PaymentService")
    assert cls.kind == "class"
    assert cls.docstring == "Orchestrates payment intent creation and confirmation."
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/test_backend_typescript.py -v`
Expected: FAIL — `ImportError: cannot import name 'extract_typescript'`.

- [ ] **Step 3: Write the query file**

```scheme
; packages/c4parser/c4parser/static_facts/queries/typescript.scm
(import_statement source: (string) @import)
(function_declaration) @def
(class_declaration) @def
```

- [ ] **Step 4: Append to `backend.py`**

```python
# Append to packages/c4parser/c4parser/static_facts/backend.py

_TYPESCRIPT_QUERY = (_QUERIES_DIR / "typescript.scm").read_text()


def _typescript_docstring(def_node, source_bytes: bytes) -> str:
    prev = def_node.prev_sibling
    if prev is not None and prev.type == "comment":
        text = _node_text(prev, source_bytes)
        if text.startswith("/**"):
            return text.strip("/* \n\t")
    return ""


def extract_typescript(file_path: str, source: str) -> tuple[list[str], list[DefFact]]:
    parser = get_parser("typescript")
    language = get_language("typescript")
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)

    query = language.query(_TYPESCRIPT_QUERY)
    captures = query.captures(tree.root_node)

    imports = [_node_text(n, source_bytes).strip("'\"") for n in captures.get("import", [])]

    defines: list[DefFact] = []
    for node in captures.get("def", []):
        name_node = node.child_by_field_name("name")
        name = _node_text(name_node, source_bytes) if name_node else ""
        kind = "class" if node.type == "class_declaration" else "function"
        defines.append(DefFact(name=name, kind=kind, docstring=_typescript_docstring(node, source_bytes)))

    return imports, defines
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/test_backend_typescript.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full static_facts suite so far**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/ -v`
Expected: PASS, all tests from Tasks 1-5 green together.

- [ ] **Step 7: Commit**

```bash
git add packages/c4parser/c4parser/static_facts/backend.py packages/c4parser/c4parser/static_facts/queries/typescript.scm packages/c4parser/tests/static_facts/test_backend_typescript.py
git commit -m "feat(c4parser): add tree-sitter TypeScript extraction backend"
```

---

## Task 6: Wire orchestration — full `extract_facts()`

**Files:**
- Modify: `packages/c4parser/c4parser/static_facts/__init__.py`
- Test: `packages/c4parser/tests/static_facts/test_extract_facts.py`

**Interfaces:**
- Consumes: `noise.top_level_name/is_known_external/is_stdlib` (Task 2), `resolver.detect_package_roots/resolve_python_import/resolve_typescript_import` (Task 3), `backend.extract_python/extract_typescript` (Tasks 4-5).
- Produces: fully working `extract_facts(root: str, files: list[str]) -> list[FileFacts]` — consumed by Task 7 (MCP collapse).

- [ ] **Step 1: Write the failing tests**

```python
# packages/c4parser/tests/static_facts/test_extract_facts.py
from pathlib import Path

from c4parser.static_facts import extract_facts


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def test_extract_facts_resolves_internal_import(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    init_file = _write(tmp_path / "apps" / "subscriptions" / "__init__.py", "")
    caller = _write(
        tmp_path / "apps" / "payments" / "service.py",
        "from apps.subscriptions import manager\n\ndef f():\n    pass\n",
    )
    facts = extract_facts(str(tmp_path), [str(caller)])
    assert len(facts) == 1
    imp = facts[0].imports[0]
    assert imp.kind == "internal"
    assert imp.resolved_path == str(init_file)


def test_extract_facts_keeps_known_external(tmp_path):
    caller = _write(tmp_path / "service.py", "import stripe\n")
    facts = extract_facts(str(tmp_path), [str(caller)])
    kinds = {imp.raw: imp.kind for imp in facts[0].imports}
    assert kinds["stripe"] == "external_known"


def test_extract_facts_drops_stdlib_noise(tmp_path):
    caller = _write(tmp_path / "service.py", "import os\nimport stripe\n")
    facts = extract_facts(str(tmp_path), [str(caller)])
    raws = [imp.raw for imp in facts[0].imports]
    assert "os" not in raws
    assert "stripe" in raws


def test_extract_facts_drops_unresolved_unknown_generic(tmp_path):
    caller = _write(tmp_path / "service.py", "import some_random_generic_lib\n")
    facts = extract_facts(str(tmp_path), [str(caller)])
    assert facts[0].imports == []


def test_extract_facts_captures_docstrings(tmp_path):
    caller = _write(
        tmp_path / "service.py",
        'def create_intent(amount):\n    """Creates a Stripe payment intent."""\n    pass\n',
    )
    facts = extract_facts(str(tmp_path), [str(caller)])
    assert facts[0].defines[0].docstring == "Creates a Stripe payment intent."


def test_extract_facts_skips_malformed_file(tmp_path):
    caller = _write(tmp_path / "broken.py", "def f(:\n    this is not python\n")
    # Should not raise — either returns [] facts for the file or empty imports/defines.
    facts = extract_facts(str(tmp_path), [str(caller)])
    assert isinstance(facts, list)


def test_extract_facts_unknown_extension_skipped(tmp_path):
    caller = _write(tmp_path / "README.md", "# hello\n")
    facts = extract_facts(str(tmp_path), [str(caller)])
    assert facts == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/test_extract_facts.py -v`
Expected: FAIL — imports/defines empty because `extract_facts` still returns `[]` unconditionally (Task 1 stub).

- [ ] **Step 3: Rewrite `extract_facts` in `__init__.py`**

```python
# packages/c4parser/c4parser/static_facts/__init__.py
"""
@c3:component
name: Static Facts Extractor
container: Annotation Parser
technology: tree-sitter
description: Statically extracts imports, top-level definitions, and adjacent docstrings from source files (Python, TypeScript) as an unverified candidate signal — never a source of truth. Isolated in its own subpackage behind extract_facts() so tree-sitter (an optional dependency) can be dropped without breaking annotation scanning or building.
"""
import importlib.util
from pathlib import Path

from . import noise, resolver
from .types import DefFact, FileFacts, ImportFact

__all__ = ["extract_facts", "FileFacts", "ImportFact", "DefFact"]

_EXT_LANGUAGE = {".py": "python", ".ts": "typescript", ".tsx": "typescript"}


def _backend_available() -> bool:
    return importlib.util.find_spec("tree_sitter_language_pack") is not None


def extract_facts(root: str, files: list[str]) -> list[FileFacts]:
    """
    Given a repo root and a list of file paths, return statically-extracted
    candidate facts for each recognized (Python/TypeScript) file. Returns []
    if the optional `static-facts` extra isn't installed, or if `files` is
    empty. Never raises on a per-file parse error — that file is skipped.
    """
    if not _backend_available() or not files:
        return []

    from . import backend  # local import: only touches tree-sitter once we know it's installed

    package_roots = resolver.detect_package_roots(root)
    results: list[FileFacts] = []

    for file_path in files:
        language = _EXT_LANGUAGE.get(Path(file_path).suffix)
        if language is None:
            continue
        try:
            source = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        try:
            if language == "python":
                raw_imports, defines = backend.extract_python(file_path, source)
            else:
                raw_imports, defines = backend.extract_typescript(file_path, source)
        except Exception:
            continue  # malformed syntax — skip this file, keep going

        kept_imports: list[ImportFact] = []
        for raw in raw_imports:
            if language == "python":
                resolved = resolver.resolve_python_import(raw, file_path, package_roots)
            else:
                resolved = resolver.resolve_typescript_import(raw, file_path, package_roots)

            if resolved is not None:
                kept_imports.append(ImportFact(raw=raw, resolved_path=resolved, kind="internal"))
                continue

            top = noise.top_level_name(raw, language)
            if noise.is_known_external(top, language):
                kept_imports.append(ImportFact(raw=raw, resolved_path=None, kind="external_known"))
            # else: stdlib or unknown generic — dropped as noise

        results.append(FileFacts(file=file_path, imports=kept_imports, defines=defines))

    return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/c4parser && uv run pytest tests/static_facts/ -v`
Expected: PASS — full `static_facts` suite green.

- [ ] **Step 5: Commit**

```bash
git add packages/c4parser/c4parser/static_facts/__init__.py packages/c4parser/tests/static_facts/test_extract_facts.py
git commit -m "feat(c4parser): wire static_facts extraction, resolution, and noise filtering"
```

---

## Task 7: Component-level collapse (`mcp/static_facts.py`)

**Files:**
- Create: `mcp/static_facts.py`
- Create: `cli/seeforce_cli/mcp_static_facts.py` (identical logic, `seeforce_cli`-prefixed import — mirrors the existing `ownership.py`/`mcp_ownership.py` pattern)
- Test: `cli/tests/test_mcp_static_facts.py`

**Interfaces:**
- Consumes: `FileFacts`/`ImportFact` shape from `c4parser.static_facts` (Task 6) — duck-typed (`.file`, `.imports`, each with `.resolved_path`, `.raw`), and an `infer_owner(file_path, ws) -> dict` callable matching `ownership.py`'s existing signature (keys: `confidence`, `kind`, `element`, `candidates`).
- Produces: `collapse_to_components(facts: list, ws: dict, infer_owner) -> list[dict]` — each dict has keys `from_file`, `from_component`, `raw_import`, `to_file`, `to_component`. Consumed by Task 8.

- [ ] **Step 1: Write the failing tests**

```python
# cli/tests/test_mcp_static_facts.py
from seeforce_cli.mcp_static_facts import collapse_to_components


class _FakeImport:
    def __init__(self, raw, resolved_path):
        self.raw = raw
        self.resolved_path = resolved_path


class _FakeFileFacts:
    def __init__(self, file, imports):
        self.file = file
        self.imports = imports
        self.defines = []


def _owner(name):
    return {"confidence": "exact", "kind": "component", "element": {"name": name}, "candidates": []}


_UNKNOWN = {"confidence": "unknown", "kind": None, "element": None, "candidates": []}


def test_collapse_keeps_cross_component_edge():
    facts = [_FakeFileFacts("a.py", [_FakeImport("pkg.b", "b.py")])]

    def infer_owner(file_path, ws):
        return _owner("ComponentA") if file_path == "a.py" else _owner("ComponentB")

    edges = collapse_to_components(facts, {}, infer_owner)
    assert len(edges) == 1
    assert edges[0]["from_component"] == "ComponentA"
    assert edges[0]["to_component"] == "ComponentB"


def test_collapse_drops_intra_component_edge():
    facts = [_FakeFileFacts("a.py", [_FakeImport("pkg.b", "b.py")])]

    def infer_owner(file_path, ws):
        return _owner("SameComponent")

    edges = collapse_to_components(facts, {}, infer_owner)
    assert edges == []


def test_collapse_keeps_unknown_owner_on_cold_start():
    facts = [_FakeFileFacts("a.py", [_FakeImport("pkg.b", "b.py")])]

    def infer_owner(file_path, ws):
        return _UNKNOWN

    edges = collapse_to_components(facts, {}, infer_owner)
    assert len(edges) == 1
    assert edges[0]["from_component"] is None
    assert edges[0]["to_component"] is None


def test_collapse_external_known_import_has_no_to_component():
    facts = [_FakeFileFacts("a.py", [_FakeImport("stripe", None)])]

    def infer_owner(file_path, ws):
        return _owner("ComponentA")

    edges = collapse_to_components(facts, {}, infer_owner)
    assert len(edges) == 1
    assert edges[0]["to_file"] is None
    assert edges[0]["to_component"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd cli && uv run pytest tests/test_mcp_static_facts.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'seeforce_cli.mcp_static_facts'`.

- [ ] **Step 3: Write `cli/seeforce_cli/mcp_static_facts.py`**

```python
# cli/seeforce_cli/mcp_static_facts.py
"""
@c3:component
name: Static Facts Bridge
container: MCP Server
technology: Python
description: Collapses the file-level import graph from Static Facts Extractor into component-level candidate edges by resolving each endpoint through file ownership inference, dropping intra-component pairs so only cross-component candidates reach the LLM.
uses:
- Annotation Parser/Static Facts Extractor: "requests statically-extracted imports and definitions for the given files"
"""


def collapse_to_components(facts: list, ws: dict, infer_owner) -> list[dict]:
    """
    facts: list of FileFacts-shaped objects (from c4parser.static_facts.extract_facts)
    ws: workspace dict (from fetch_workspace())
    infer_owner: infer_owner(file_path, ws) -> dict, matching ownership.py's signature

    Returns one dict per surviving candidate edge: from_file, from_component,
    raw_import, to_file, to_component. Intra-component edges (both endpoints
    resolve to the same known component) are dropped. When either endpoint's
    owner is unknown (no annotations yet — cold start), the edge is kept with
    component=None: there's nothing to collapse against yet, so it passes
    through as a raw recall signal.
    """
    edges: list[dict] = []
    for file_facts in facts:
        from_owner = infer_owner(file_facts.file, ws)
        from_component = from_owner["element"]["name"] if from_owner["element"] else None

        for imp in file_facts.imports:
            to_component = None
            if imp.resolved_path is not None:
                to_owner = infer_owner(imp.resolved_path, ws)
                to_component = to_owner["element"]["name"] if to_owner["element"] else None
                if from_component is not None and from_component == to_component:
                    continue

            edges.append({
                "from_file": file_facts.file,
                "from_component": from_component,
                "raw_import": imp.raw,
                "to_file": imp.resolved_path,
                "to_component": to_component,
            })

    return edges
```

- [ ] **Step 4: Copy it to `mcp/static_facts.py`**

Same content, same filename — this module has no import-path differences to adjust (it takes `infer_owner` as a parameter rather than importing it), so it's a literal copy:

```bash
cp cli/seeforce_cli/mcp_static_facts.py mcp/static_facts.py
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd cli && uv run pytest tests/test_mcp_static_facts.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add cli/seeforce_cli/mcp_static_facts.py mcp/static_facts.py cli/tests/test_mcp_static_facts.py
git commit -m "feat(mcp): add static-facts component collapse"
```

---

## Task 8: Wire the MCP tool + dependency plumbing

**Files:**
- Modify: `cli/seeforce_cli/mcp_server.py`
- Modify: `mcp/server.py`
- Modify: `cli/pyproject.toml`
- Modify: `mcp/requirements.txt`
- Test: `cli/tests/test_mcp_static_facts_tool.py`

**Interfaces:**
- Consumes: `c4parser.static_facts.extract_facts` (Task 6), `collapse_to_components` (Task 7), existing `infer_owner`/`fetch_workspace` (pre-existing in both `mcp_ownership.py`/`ownership.py` and `mcp_client.py`/`client.py`).
- Produces: `get_static_facts_for_files(file_paths: list[str]) -> str`, registered as an MCP tool in both server files.

- [ ] **Step 1: Add the dependency plumbing**

`cli/pyproject.toml` — change the `seeforce-c4parser` dependency line to request the extra:

```toml
dependencies = [
    "click>=8.1",
    "httpx>=0.27",
    "seeforce-c4parser[static-facts]>=0.1.0",
    "mcp>=2.0",
]
```

`mcp/requirements.txt` — add an editable install of `packages/c4parser` with the extra, so the repo's own dogfooding MCP server can import it too:

```
mcp>=1.0.0
httpx>=0.27.0
-e ../packages/c4parser[static-facts]
```

Run: `cd cli && uv sync` then `cd ../mcp && pip install -r requirements.txt` (or the project's existing mcp/ setup command, if different — check for a `mcp/README.md` or Makefile target before falling back to raw pip).

- [ ] **Step 2: Write the failing test**

```python
# cli/tests/test_mcp_static_facts_tool.py
from unittest.mock import AsyncMock, patch

import pytest

from seeforce_cli.mcp_server import get_static_facts_for_files

_EMPTY_WS = {"model": {"softwareSystems": []}}


@pytest.mark.asyncio
async def test_get_static_facts_for_files_no_facts_message(tmp_path):
    caller = tmp_path / "README.md"
    caller.write_text("# hello\n")
    with patch("seeforce_cli.mcp_server.fetch_workspace", new=AsyncMock(return_value=_EMPTY_WS)):
        result = await get_static_facts_for_files([str(caller)])
    assert "unavailable" in result.lower() or "no facts" in result.lower()


@pytest.mark.asyncio
async def test_get_static_facts_for_files_labels_candidate(tmp_path):
    caller = tmp_path / "service.py"
    caller.write_text('def f():\n    """does a thing"""\n    pass\n')
    with patch("seeforce_cli.mcp_server.fetch_workspace", new=AsyncMock(return_value=_EMPTY_WS)):
        result = await get_static_facts_for_files([str(caller)])
    assert "CANDIDATE" in result
    assert "does a thing" in result
```

(If the project has no `pytest-asyncio` configured yet, add it: `cd cli && uv add --optional dev pytest-asyncio` and add `[tool.pytest.ini_options]\nasyncio_mode = "auto"` to `cli/pyproject.toml`.)

- [ ] **Step 3: Run test to verify it fails**

Run: `cd cli && uv run pytest tests/test_mcp_static_facts_tool.py -v`
Expected: FAIL — `ImportError: cannot import name 'get_static_facts_for_files'`.

- [ ] **Step 4: Add the tool to `cli/seeforce_cli/mcp_server.py`**

Add these imports near the top (alongside the existing `seeforce_cli.mcp_*` imports):

```python
import os
from c4parser.static_facts import extract_facts
from seeforce_cli.mcp_static_facts import collapse_to_components
```

Add the tool function after `get_architecture_for_files`:

```python
@server.tool()
async def get_static_facts_for_files(file_paths: list[str]) -> str:
    """
    Given a list of files, returns a statically-extracted CANDIDATE signal:
    imports observed in the code, resolved to components where possible, plus
    docstrings for any functions/classes defined in those files.

    This is NOT verified truth — it is a recall aid to catch relations you
    might otherwise miss. It cannot see dynamic wiring (DI, reflection,
    config-driven routes, message-bus subscriptions), and an edge here may be
    import-only with no real call site. Confirm each candidate against actual
    usage in the code before treating it as an architectural relation.
    """
    ws = await fetch_workspace()
    facts = extract_facts(os.getcwd(), file_paths)
    if not facts:
        return "Static analysis unavailable (tree-sitter not installed, or no facts extracted for these files)."

    edges = collapse_to_components(facts, ws, infer_owner)

    lines: list[str] = ["⚠ CANDIDATE signal, not verified truth — confirm before annotating.\n"]
    for file_facts in facts:
        lines.append(f"=== {file_facts.file} ===")
        if file_facts.defines:
            lines.append("Definitions:")
            for d in file_facts.defines:
                doc = f" — {d.docstring}" if d.docstring else ""
                lines.append(f"  {d.kind} {d.name}{doc}")
        file_edges = [e for e in edges if e["from_file"] == file_facts.file]
        if file_edges:
            lines.append("Candidate edges:")
            for e in file_edges:
                dest = e["to_component"] or e["to_file"] or e["raw_import"]
                lines.append(f"  → {dest} (import: {e['raw_import']})")
        lines.append("")

    return "\n".join(lines)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd cli && uv run pytest tests/test_mcp_static_facts_tool.py -v`
Expected: PASS.

- [ ] **Step 6: Mirror the same change into `mcp/server.py`**

Add near the top (root copy uses bare-module imports via its `sys.path.insert` — match that style):

```python
import os
from static_facts import collapse_to_components
```

and add, right after the existing `sys.path.insert(0, str(Path(__file__).parent))` line, a second path insert so `c4parser` resolves from the editable install:

```python
from c4parser.static_facts import extract_facts
```

Add the identical `get_static_facts_for_files` tool function (same body as Step 4) after the existing `get_architecture_for_files` in `mcp/server.py`.

- [ ] **Step 7: Run the full cli test suite**

Run: `cd cli && uv run pytest tests/ -v`
Expected: PASS, no regressions in existing tests.

- [ ] **Step 8: Commit**

```bash
git add cli/seeforce_cli/mcp_server.py mcp/server.py cli/pyproject.toml cli/uv.lock mcp/requirements.txt cli/tests/test_mcp_static_facts_tool.py
git commit -m "feat(mcp): expose get_static_facts_for_files tool"
```

---

## Task 9: Update the annotator prompt

**Files:**
- Modify: `cli/seeforce_cli/prompts/c4_annotator.md`

**Interfaces:**
- Consumes: nothing (documentation-only change).
- Produces: nothing consumed by other tasks — this is the last task.

- [ ] **Step 1: Locate the insertion point**

Find Step 6 of the `## Process` section (currently: `6. **Infer relations** from imports, function calls, channel sends, HTTP clients, DB queries — runtime flow only`).

- [ ] **Step 2: Replace Step 6 with the expanded version**

```markdown
6. **Infer relations** from imports, function calls, channel sends, HTTP clients, DB queries — runtime flow only. If the `get_static_facts_for_files` MCP tool is available, cross-check its candidate edges for the files you're annotating before finalizing relations: it catches imports you might otherwise miss (a recall aid), but it is NOT verified truth. Confirm each candidate reflects real runtime usage — not just an unused import — before annotating it. It also cannot see dynamic wiring (DI containers, plugin registries, reflection, config-driven routes, message-bus subscriptions); keep searching for those independently. A missing static candidate is not evidence that a relation doesn't exist.
```

- [ ] **Step 3: Verify the edit landed**

Run: `grep -n "get_static_facts_for_files" cli/seeforce_cli/prompts/c4_annotator.md`
Expected: one match, inside the rewritten Step 6.

- [ ] **Step 4: Commit**

```bash
git add cli/seeforce_cli/prompts/c4_annotator.md
git commit -m "docs(prompt): tell the annotator to cross-check static-facts candidates"
```

---

## Post-plan verification

- [ ] Run `cd packages/c4parser && uv run pytest tests/ -v` — full green.
- [ ] Run `cd cli && uv run pytest tests/ -v` — full green.
- [ ] Manually smoke-test: from this repo's root, with the MCP server reloaded, call `get_static_facts_for_files` on a real file (e.g. `backend/apps/graph/views/graph.py`) and confirm the output is labeled CANDIDATE and shows plausible imports/docstrings.
