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


def test_extract_facts_captures_relative_imports(tmp_path):
    """`from . import x` / `from .mod import y` produce a relative_import node, not a
    dotted_name — they were invisible to the query and never captured."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    pkg = tmp_path / "apps" / "subscriptions"
    init_file = _write(pkg / "__init__.py", "")
    sibling = _write(pkg / "types.py", "")
    parent_mod = _write(tmp_path / "apps" / "shared.py", "")
    caller = _write(
        pkg / "manager.py",
        "from . import helpers\nfrom .types import Thing\nfrom ..shared import Base\n",
    )

    facts = extract_facts(str(tmp_path), [str(caller)])
    by_raw = {imp.raw: imp for imp in facts[0].imports}
    assert set(by_raw) == {".", ".types", "..shared"}
    assert by_raw["."].resolved_path == str(init_file)
    assert by_raw[".types"].resolved_path == str(sibling)
    assert by_raw["..shared"].resolved_path == str(parent_mod)
    assert all(imp.kind == "internal" for imp in by_raw.values())


def test_extract_facts_resolves_flat_sibling_without_package_root(tmp_path):
    """Scripts in a directory with no pyproject.toml above them (this repo's own
    mcp/*.py) must still surface their same-directory imports."""
    scripts = tmp_path / "mcp"
    client = _write(scripts / "client.py", "")
    caller = _write(
        scripts / "server.py",
        "from client import fetch_workspace\n\ndef run():\n    pass\n",
    )
    facts = extract_facts(str(tmp_path), [str(caller)])
    imp = facts[0].imports[0]
    assert imp.raw == "client"
    assert imp.kind == "internal"
    assert imp.resolved_path == str(client)
