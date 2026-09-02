import ast
from pathlib import Path

import pytest

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


# --- twin-file conventions (mcp/*.py <-> seeforce_cli/mcp_*.py) ---

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ROOT_TWIN = _REPO_ROOT / "mcp" / "static_facts.py"
_CLI_TWIN = _REPO_ROOT / "cli" / "seeforce_cli" / "mcp_static_facts.py"
_ROOT_SERVER = _REPO_ROOT / "mcp" / "server.py"

_needs_repo = pytest.mark.skipif(
    not (_ROOT_TWIN.exists() and _CLI_TWIN.exists() and _ROOT_SERVER.exists()),
    reason="repo checkout not available (running from an installed package)",
)


@_needs_repo
def test_only_one_twin_declares_the_static_facts_bridge_component():
    """Annotating both twins yields two same-named components in the same container.
    Convention (see mcp/server.py vs mcp_server.py): only the mcp/ copy is annotated."""
    bridges = [e for e in _scan() if getattr(e, "name", None) == "Static Facts Bridge"]
    assert [e.source_file for e in bridges] == ["mcp/static_facts.py"]


@_needs_repo
def test_static_facts_bridge_annotation_claims_no_extractor_edge():
    """collapse_to_components takes already-extracted facts as a parameter and never
    reaches the extractor, so a `uses:` edge to it would be an invented relation."""
    imported = {
        n.module
        for n in ast.walk(ast.parse(_ROOT_TWIN.read_text()))
        if isinstance(n, ast.ImportFrom)
    }
    assert not any((m or "").startswith("c4parser") for m in imported), imported

    bridge = next(e for e in _scan() if getattr(e, "name", None) == "Static Facts Bridge")
    used_names = {u if isinstance(u, str) else next(iter(u)) for u in bridge.uses}
    assert "Static Facts Extractor" not in used_names, bridge.uses
    assert "Annotation Parser/Static Facts Extractor" not in used_names, bridge.uses


@_needs_repo
def test_mcp_server_container_annotation_declares_annotation_parser_edge():
    """mcp/server.py imports and calls c4parser.static_facts.extract_facts — a real
    cross-container dependency that must appear in its @c2:container uses list."""
    assert "from c4parser.static_facts import extract_facts" in _ROOT_SERVER.read_text()
    container = next(
        e for e in _scan()
        if getattr(e, "name", None) == "MCP Server" and e.source_file == "mcp/server.py"
    )
    targets = {k for u in container.uses for k in u if k != "technology"}
    assert "Annotation Parser" in targets, targets


@_needs_repo
def test_twin_collapse_functions_stay_identical():
    """The two copies may differ in their annotation/comment header, but the shipped
    logic must not drift apart."""
    assert _function_source(_ROOT_TWIN, "collapse_to_components") == \
        _function_source(_CLI_TWIN, "collapse_to_components")


@_needs_repo
@pytest.mark.parametrize(
    "name", ["_MAX_DOC_CHARS", "_summarize_docstring", "get_static_facts_for_files"]
)
def test_static_facts_tool_stays_identical_across_server_twins(name):
    """mcp/server.py has no test suite of its own; the CLI twin's tests only guard the
    shipped copy. Pin them together so a fix landing in one can't skip the other."""
    cli_server = _REPO_ROOT / "cli" / "seeforce_cli" / "mcp_server.py"
    assert _function_source(_ROOT_SERVER, name) == _function_source(cli_server, name)


def _scan():
    """Parse the repo's real annotations, the same way `seeforce scan` does."""
    from c4parser.scanner import scan

    return scan(str(_REPO_ROOT))


def _function_source(path: Path, name: str) -> str:
    """Normalized source of a top-level function or constant. Decorators are dropped —
    the two server twins share bodies but sit behind separate `server` instances."""
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if _defines(n, name))
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        node.decorator_list = []
    return ast.unparse(node)


def _defines(node: ast.stmt, name: str) -> bool:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name == name
    if isinstance(node, ast.Assign):
        return any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
    return False
