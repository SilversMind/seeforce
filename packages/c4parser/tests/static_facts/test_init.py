from pathlib import Path

import c4parser.static_facts as sf


def test_extract_facts_degrades_without_backend(monkeypatch):
    monkeypatch.setattr(sf, "_backend_available", lambda: False)
    assert sf.extract_facts(".", ["whatever.py"]) == []


def test_extract_facts_empty_file_list():
    assert sf.extract_facts(".", []) == []


def test_tree_sitter_pin_floor_covers_query_cursor_api():
    """backend.py uses tree_sitter.Query + tree_sitter.QueryCursor, which only exist
    from tree-sitter 0.25 onward. A lower pin lets a 0.23/0.24 install through, where
    every extraction fails silently and the MCP tool reports 'tree-sitter not
    installed' even though it is."""
    import tomllib

    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    specs = data["project"]["optional-dependencies"]["static-facts"]
    pin = next(
        s for s in specs
        if s.startswith("tree-sitter") and not s.startswith("tree-sitter-")
    )
    floor = pin.split(">=", 1)[1].strip()
    assert tuple(int(p) for p in floor.split(".")) >= (0, 25), pin
