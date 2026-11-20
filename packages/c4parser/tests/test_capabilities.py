"""A description's bullets are capabilities: parsed into a tree, counted by leaf, diffed bullet by bullet."""
from c4parser import (
    changed_capabilities,
    count_capabilities,
    diff_capabilities,
    parse_capabilities,
)

NESTED = "- Serves the REST API for:\n  - Project CRUD\n  - GitHub import\n- Persists data"


def test_parse_builds_a_tree():
    assert parse_capabilities(NESTED) == [
        {"text": "Serves the REST API for:", "children": [
            {"text": "Project CRUD", "children": []},
            {"text": "GitHub import", "children": []},
        ]},
        {"text": "Persists data", "children": []},
    ]


def test_prose_has_no_capabilities():
    assert parse_capabilities("Serves the API.") == []


def test_count_skips_grouping_parents():
    assert count_capabilities(parse_capabilities(NESTED)) == 3


def test_identical_lists_have_no_changes():
    assert changed_capabilities(diff_capabilities(NESTED, NESTED)) == []


def test_added_bullet():
    tree = diff_capabilities("- a\n- b", "- a\n- b\n- c")
    assert [n["status"] for n in tree] == ["unchanged", "unchanged", "added"]


def test_removed_bullet_keeps_its_place():
    tree = diff_capabilities("- a\n- gone\n- b", "- a\n- b")
    assert [(n["text"], n["status"]) for n in tree] == [("a", "unchanged"), ("gone", "removed"), ("b", "unchanged")]


def test_close_wording_is_a_reword():
    tree = diff_capabilities("- Attaches edges to borders", "- Attaches each edge to borders")
    assert tree == [{
        "text": "Attaches each edge to borders", "status": "reworded",
        "before": "Attaches edges to borders", "children": [],
    }]


def test_an_extended_bullet_is_a_reword():
    tree = diff_capabilities("- Renders the delta", "- Renders the delta, one row per changed capability or action")
    assert [n["status"] for n in tree] == ["reworded"]


def test_unrelated_wording_is_a_remove_and_an_add():
    tree = diff_capabilities("- Shows a tooltip", "- Persists the overlay")
    assert sorted(n["status"] for n in tree) == ["added", "removed"]


def test_children_diff_under_a_reworded_parent():
    rows = changed_capabilities(diff_capabilities(
        "- Serves the API for:\n  - CRUD\n  - Import",
        "- Serves the REST API for:\n  - CRUD\n  - Sync",
    ))
    assert ("reworded", "Serves the REST API for:", "Serves the API for:") in rows
    assert ("removed", "Import", "") in rows
    assert ("added", "Sync", "") in rows


def test_an_edge_phrase_is_one_action():
    rows = changed_capabilities(diff_capabilities("reads K", "- reads K\n- writes K"))
    assert rows == [("added", "writes K", "")]
