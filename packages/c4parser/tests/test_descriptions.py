"""Descriptions are `- ` bullet lists, written either as a literal block or as a YAML list."""
from c4parser.builder import build, find_unreadable_descriptions, merge_flows
from c4parser.scanner import format_description, scan

SYSTEM = '"""\n@c1:system\nname: S\nshort_desc: A system\ndescription: |\n  - Does one thing\n"""\n'
EXTERNAL = '"""\n@c1:external\nname: E\nshort_desc: An external\ndescription: |\n  - Stores data\n"""\n'
CONTAINER = '"""\n@c2:container\nname: C\nsystem: S\nshort_desc: A container\ndescription:\n{desc}uses:\n{uses}"""\n'
COMPONENT = '"""\n@c3:component\nname: K\ncontainer: C\nshort_desc: A component\ndescription: |\n  - Holds K\n"""\n'

NESTED_LIST = """\
  - Serves the REST API for:
    - Project CRUD
    - GitHub:
      - Import
      - Sync
  - Persists data in the Database
"""


def _workspace(tmp_path, desc, edge="stores records in E", uses=None):
    (tmp_path / "s.py").write_text(SYSTEM)
    (tmp_path / "e.py").write_text(EXTERNAL)
    (tmp_path / "c.py").write_text(CONTAINER.format(desc=desc, uses=uses or f'- E: "{edge}"\n'))
    (tmp_path / "k.py").write_text(COMPONENT)
    return build(scan(str(tmp_path)))


def _container(workspace):
    system = next(s for s in workspace["model"]["softwareSystems"] if s["name"] == "S")
    return system["containers"][0]


def test_yaml_list_becomes_nested_bullets(tmp_path):
    ws = _workspace(tmp_path, NESTED_LIST)
    assert _container(ws)["description"] == (
        "- Serves the REST API for:\n"
        "  - Project CRUD\n"
        "  - GitHub:\n"
        "    - Import\n"
        "    - Sync\n"
        "- Persists data in the Database"
    )
    assert find_unreadable_descriptions(ws) == []


def test_literal_block_is_kept_as_written():
    assert format_description("  - a\n    - b\n  - c\n") == "- a\n  - b\n- c"


def test_prose_description_is_flagged(tmp_path):
    ws = _workspace(tmp_path, "  Serves the API.\n")
    assert any("'C' description is not a bullet list" in w for w in find_unreadable_descriptions(ws))


def test_long_edge_description_is_flagged(tmp_path):
    ws = _workspace(tmp_path, NESTED_LIST, edge="x" * 101)
    assert any("101-char edge flow" in w for w in find_unreadable_descriptions(ws))


def test_list_edge_becomes_bullets(tmp_path):
    ws = _workspace(tmp_path, NESTED_LIST, uses='- E:\n  - "stores records"\n  - "reads records"\n')
    rel = _container(ws)["relationships"][0]
    assert rel["description"] == "- stores records\n- reads records"
    assert find_unreadable_descriptions(ws) == []


def test_semicolon_edge_is_flagged(tmp_path):
    ws = _workspace(tmp_path, NESTED_LIST, edge="stores records; reads records")
    assert any("joining flows with ';'" in w for w in find_unreadable_descriptions(ws))


def test_merge_flows_dedupes_and_lists():
    assert merge_flows(["reads K"]) == "reads K"
    assert merge_flows(["- reads K\n- writes K", "reads K"]) == "- reads K\n- writes K"
