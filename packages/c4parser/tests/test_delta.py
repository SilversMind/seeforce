import dataclasses
import json
from pathlib import Path

import pytest
from c4parser.delta import (
    COMPARED_FIELDS,
    Delta,
    Element,
    diff,
    flatten,
    pair,
    render_markdown,
)
from c4parser.exceptions import C4ValidationError


def _ws(**model):
    return {"name": "T", "model": model}


def test_flatten_walks_every_level():
    ws = _ws(
        people=[{"id": "dev", "name": "Developer", "source_file": "a.py"}],
        softwareSystems=[{
            "id": "sys", "name": "Sys",
            "containers": [{
                "id": "cont", "name": "Backend", "source_file": "b.py",
                "components": [{"id": "comp", "name": "API", "source_file": "c.py"}],
            }],
        }],
    )
    got = {(e.kind, e.name, e.path) for e in flatten(ws)}
    assert got == {
        ("person", "Developer", "Developer"),
        ("system", "Sys", "Sys"),
        ("container", "Backend", "Backend (Sys)"),
        ("component", "API", "API (Backend)"),
    }


def test_flatten_captures_compared_fields_and_relations():
    ws = _ws(softwareSystems=[{
        "id": "sys", "name": "Sys",
        "containers": [{
            "id": "cont", "name": "Backend", "technology": "Django",
            "description": "serves the API", "short_desc": "API", "tags": "Container",
            "source_file": "b.py",
            "relationships": [{"destinationId": "db", "description": "reads", "technology": "ORM"}],
        }],
    }])
    cont = next(e for e in flatten(ws) if e.kind == "container")
    assert cont.fields["technology"] == "Django"
    assert cont.fields["description"] == "serves the API"
    assert set(cont.fields) == set(COMPARED_FIELDS)
    assert cont.relations == [{"destinationId": "db", "description": "reads", "technology": "ORM"}]


def test_flatten_missing_field_becomes_empty_string():
    ws = _ws(softwareSystems=[{"id": "sys", "name": "Sys"}])
    sys_el = flatten(ws)[0]
    assert sys_el.fields["technology"] == ""
    assert sys_el.source_file == ""


# Review Focus 3
@pytest.mark.parametrize("model", [{}, {"people": None, "softwareSystems": None}, {"people": []}])
def test_flatten_tolerates_absent_collections(model):
    assert flatten({"model": model}) == []


# Review Focus 2
@pytest.mark.parametrize("ws", [{}, {"model": None}, {"model": []}, {"model": "nope"}])
def test_flatten_rejects_a_workspace_without_a_model(ws):
    with pytest.raises(C4ValidationError, match="model"):
        flatten(ws)


@pytest.mark.parametrize("ws", [[], None, "nope", 42])
def test_flatten_rejects_a_non_object_workspace(ws):
    with pytest.raises(C4ValidationError, match="JSON object"):
        flatten(ws)


def _el(kind, name, source_file="", id_=""):
    return Element(kind=kind, name=name, path=name, id=id_ or name, source_file=source_file, fields={}, relations=[])


def test_pair_matches_on_source_file_so_a_rename_is_a_pair():
    base = [_el("component", "Glossary", "lex.tsx", "c-glossary")]
    head = [_el("component", "Lexicon", "lex.tsx", "c-lexicon")]
    pairs, added, removed = pair(base, head)
    assert [(b.name, h.name) for b, h in pairs] == [("Glossary", "Lexicon")]
    assert (added, removed) == ([], [])


def test_pair_separates_kinds_sharing_one_file():
    base = [_el("container", "Backend", "init.py"), _el("person", "Developer", "init.py")]
    pairs, added, removed = pair(base, list(base))
    assert len(pairs) == 2
    assert (added, removed) == ([], [])


def test_pair_falls_back_to_name_inside_a_multi_element_bucket():
    base = [_el("component", "Tool Handlers", "mcp.py"), _el("component", "Static Facts", "mcp.py")]
    head = [_el("component", "Tool Handlers", "mcp.py"), _el("component", "Static Facts", "mcp.py")]
    pairs, added, removed = pair(base, head)
    assert {b.name for b, _ in pairs} == {"Tool Handlers", "Static Facts"}
    assert (added, removed) == ([], [])


def test_rename_inside_a_multi_element_bucket_degrades_to_remove_plus_add():
    base = [_el("component", "Tool Handlers", "mcp.py"), _el("component", "Static Facts", "mcp.py")]
    head = [_el("component", "Tool Handlers", "mcp.py"), _el("component", "Static Facts Query", "mcp.py")]
    pairs, added, removed = pair(base, head)
    assert [b.name for b, _ in pairs] == ["Tool Handlers"]
    assert [e.name for e in removed] == ["Static Facts"]
    assert [e.name for e in added] == ["Static Facts Query"]


def test_pair_uses_the_id_when_there_is_no_source_file():
    base = [_el("system", "SeeForce", "", "seeforce")]
    head = [_el("system", "SeeForce", "", "seeforce")]
    pairs, added, removed = pair(base, head)
    assert len(pairs) == 1
    assert (added, removed) == ([], [])


def test_pair_reports_added_and_removed():
    base = [_el("component", "Gone", "gone.py")]
    head = [_el("component", "New", "new.py")]
    pairs, added, removed = pair(base, head)
    assert pairs == []
    assert [e.name for e in removed] == ["Gone"]
    assert [e.name for e in added] == ["New"]


# Review Focus 1
def test_a_simultaneous_rename_and_move_reports_remove_plus_add():
    base = [_el("component", "Glossary", "old.tsx", "c-glossary")]
    head = [_el("component", "Lexicon", "new.tsx", "c-lexicon")]
    pairs, added, removed = pair(base, head)
    assert pairs == []
    assert [e.name for e in removed] == ["Glossary"]
    assert [e.name for e in added] == ["Lexicon"]


# Review Focus 5
def test_an_uneven_bucket_keeps_every_element():
    base = [_el("component", "One", "shared.py")]
    head = [_el("component", "One", "shared.py"), _el("component", "Two", "shared.py")]
    pairs, added, removed = pair(base, head)
    assert [(b.name, h.name) for b, h in pairs] == [("One", "One")]
    assert [e.name for e in added] == ["Two"]
    assert removed == []


def _ws_component(name, **overrides):
    comp = {"id": f"c-{name.lower()}", "name": name, "source_file": "x.py"}
    comp.update(overrides)
    return {"name": "T", "model": {"softwareSystems": [{
        "id": "sys", "name": "Sys",
        "containers": [{"id": "cont", "name": "Backend", "components": [comp]}],
    }]}}


def _ws_shell():
    return {"name": "T", "model": {"softwareSystems": [{
        "id": "sys", "name": "Sys",
        "containers": [{"id": "cont", "name": "Backend", "components": []}],
    }]}}


def test_diff_reports_an_added_component():
    base = _ws_shell()
    delta = diff(base, _ws_component("API"))
    assert [e.name for e in delta.added] == ["API"]
    assert delta.removed == []
    assert delta.changed == []


def test_diff_reports_a_removed_component():
    delta = diff(_ws_component("API"), _ws_shell())
    assert [e.name for e in delta.removed] == ["API"]
    assert delta.added == []


def test_diff_names_each_changed_field():
    base = _ws_component("API", description="old", technology="REST")
    head = _ws_component("API", description="new", technology="gRPC")
    delta = diff(base, head)
    assert delta.added == [] and delta.removed == []
    change = delta.changed[0]
    assert change.path == "API (Backend)"
    assert {(f.field, f.before, f.after) for f in change.fields} == {
        ("description", "old", "new"),
        ("technology", "REST", "gRPC"),
    }


def test_a_rename_is_a_name_field_change():
    base = _ws_component("Glossary")
    head = _ws_component("Lexicon")
    head["model"]["softwareSystems"][0]["containers"][0]["components"][0]["source_file"] = "x.py"
    delta = diff(base, head)
    assert delta.added == [] and delta.removed == []
    assert [(f.field, f.before, f.after) for f in delta.changed[0].fields] == [("name", "Glossary", "Lexicon")]


def test_an_identical_workspace_yields_an_empty_delta():
    ws = _ws_component("API", description="d", technology="REST")
    delta = diff(ws, json.loads(json.dumps(ws)))
    assert delta == Delta(added=[], removed=[], changed=[], edges_added=[], edges_removed=[], edges_changed=[])


def test_delta_round_trips_through_json():
    delta = diff(_ws_component("API", description="old"), _ws_component("API", description="new"))
    restored = json.loads(json.dumps(dataclasses.asdict(delta)))
    assert restored["changed"][0]["fields"][0]["field"] == "description"


def _ws_two_components(a_name="A", b_name="B", rel_description="calls", a_file="a.py", b_file="b.py"):
    return {"name": "T", "model": {"softwareSystems": [{
        "id": "sys", "name": "Sys",
        "containers": [{
            "id": "cont", "name": "Backend",
            "components": [
                {"id": f"c-{a_name.lower()}", "name": a_name, "source_file": a_file,
                 "relationships": [{"destinationId": f"c-{b_name.lower()}",
                                    "description": rel_description, "technology": "REST"}]},
                {"id": f"c-{b_name.lower()}", "name": b_name, "source_file": b_file},
            ],
        }],
    }]}}


def test_diff_reports_an_added_relation():
    base = _ws_two_components()
    base["model"]["softwareSystems"][0]["containers"][0]["components"][0]["relationships"] = []
    delta = diff(base, _ws_two_components())
    assert [(e.source_path, e.dest_path) for e in delta.edges_added] == [("A (Backend)", "B (Backend)")]
    assert delta.edges_removed == []


def test_diff_reports_a_removed_relation():
    head = _ws_two_components()
    head["model"]["softwareSystems"][0]["containers"][0]["components"][0]["relationships"] = []
    delta = diff(_ws_two_components(), head)
    assert [(e.source_path, e.dest_path) for e in delta.edges_removed] == [("A (Backend)", "B (Backend)")]
    assert delta.edges_added == []


def test_diff_reports_a_changed_relation_description():
    delta = diff(_ws_two_components(rel_description="calls"), _ws_two_components(rel_description="polls"))
    assert delta.edges_added == [] and delta.edges_removed == []
    change = delta.edges_changed[0]
    assert (change.source_path, change.dest_path) == ("A (Backend)", "B (Backend)")
    assert [(f.field, f.before, f.after) for f in change.fields] == [("description", "calls", "polls")]


def test_renaming_a_target_does_not_touch_its_inbound_relation():
    """The cascade guard: destinationId is derived from the name, so a naive diff would
    report every inbound edge as removed and re-added."""
    delta = diff(_ws_two_components(b_name="B"), _ws_two_components(b_name="Renamed"))
    assert delta.edges_added == []
    assert delta.edges_removed == []
    assert delta.edges_changed == []
    assert [(f.field, f.before, f.after) for f in delta.changed[0].fields] == [("name", "B", "Renamed")]


# Review Focus 4
def test_a_dangling_destination_renders_the_raw_id():
    ws = _ws_two_components()
    ws["model"]["softwareSystems"][0]["containers"][0]["components"][0]["relationships"] = [
        {"destinationId": "c-nonexistent", "description": "calls", "technology": ""}
    ]
    base = _ws_two_components()
    base["model"]["softwareSystems"][0]["containers"][0]["components"][0]["relationships"] = []
    delta = diff(base, ws)
    assert [e.dest_path for e in delta.edges_added] == ["c-nonexistent"]


def test_render_says_so_when_nothing_changed():
    out = render_markdown(Delta())
    assert "No architecture changes." in out


def test_render_counts_and_groups_by_kind():
    base = _ws_shell()
    delta = diff(base, _ws_component("API", description="d"))
    out = render_markdown(delta)
    assert "## Architecture delta" in out
    assert "1 added, 0 removed, 0 changed" in out
    assert "### Components" in out
    assert "+ API (Backend) — x.py" in out


def test_render_shows_a_short_field_before_and_after():
    delta = diff(_ws_component("API", technology="REST"), _ws_component("API", technology="gRPC"))
    assert "technology: REST → gRPC" in render_markdown(delta)


def test_render_names_a_long_field_without_quoting_it():
    long_before = "x" * 90
    delta = diff(_ws_component("API", description=long_before), _ws_component("API", description="y" * 90))
    out = render_markdown(delta)
    assert "description" in out
    assert long_before not in out


def test_render_phrases_a_name_change_as_a_rename():
    delta = diff(_ws_component("Glossary"), _ws_component("Lexicon"))
    assert 'renamed from "Glossary"' in render_markdown(delta)


def test_render_lists_relations():
    base = _ws_two_components()
    base["model"]["softwareSystems"][0]["containers"][0]["components"][0]["relationships"] = []
    out = render_markdown(diff(base, _ws_two_components()))
    assert "### Relationships" in out
    assert '+ A (Backend) → B (Backend): "calls"' in out


_REPO_WORKSPACE = Path(__file__).resolve().parents[3] / ".seeforce" / "workspace.json"


def test_the_real_workspace_flattens_and_self_diffs_empty():
    ws = json.loads(_REPO_WORKSPACE.read_text(encoding="utf-8"))
    elements = flatten(ws)
    assert len(elements) > 20
    kinds = {e.kind for e in elements}
    assert {"system", "container", "component"} <= kinds
    assert all(e.kind and e.path for e in elements)
    assert "Tool Handlers" in {e.name for e in elements}
    assert diff(ws, json.loads(json.dumps(ws))) == Delta()


def test_the_real_workspace_has_a_multi_component_file():
    """The within-bucket name fallback exists for this; if it stops being true, that
    branch is no longer covered by a real case."""
    ws = json.loads(_REPO_WORKSPACE.read_text(encoding="utf-8"))
    files = [e.source_file for e in flatten(ws) if e.kind == "component" and e.source_file]
    assert len(files) != len(set(files))


def test_render_counts_a_changed_relation():
    out = render_markdown(diff(_ws_two_components(), _ws_two_components(rel_description="uses")))
    assert "0 added, 0 removed, 1 changed" in out


def test_render_counts_an_added_relation():
    head = _ws_two_components()
    head["model"]["softwareSystems"][0]["containers"][0]["components"][1]["relationships"] = [
        {"destinationId": "c-a", "description": "back"}
    ]
    assert "1 added, 0 removed, 0 changed" in render_markdown(diff(_ws_two_components(), head))


def test_elements_without_an_id_do_not_share_a_canonical_key():
    head = _ws_shell()
    head["model"]["softwareSystems"][0]["containers"][0]["components"] = [
        {"name": "A", "source_file": "a.py", "relationships": [{"destinationId": "", "description": "x"}]},
        {"name": "Z", "source_file": "z.py"},
    ]
    edge = diff(_ws_shell(), head).edges_added[0]
    assert (edge.source_path, edge.dest_path) == ("A (Backend)", "?")
