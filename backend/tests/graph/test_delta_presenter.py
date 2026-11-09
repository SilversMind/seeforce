from apps.graph.delta_presenter import decorate, element_paths
from c4parser.delta import diff


def _component(name, cid, source_file="", description="", relationships=None):
    return {
        "id": cid, "name": name, "technology": "Python", "description": description,
        "short_desc": "", "tags": "Element,Component", "source_file": source_file,
        "relationships": relationships or [],
    }


def _ws(containers):
    """One system, one person, and whatever containers the test needs."""
    return {
        "name": "Shop",
        "model": {
            "people": [{
                "id": "customer", "name": "Customer", "description": "", "tags": "Element,Person",
                "relationships": [{"id": "r-cust", "destinationId": "shop", "description": "Uses"}],
            }],
            "softwareSystems": [{
                "id": "shop", "name": "Shop", "description": "E-commerce",
                "tags": "Element,Software System", "relationships": [], "containers": containers,
            }],
        },
    }


def _container(name, cid, components, source_file="", description=""):
    return {
        "id": cid, "name": name, "technology": "Django", "description": description,
        "short_desc": "", "tags": "Element,Container", "source_file": source_file,
        "relationships": [], "components": components,
    }


BASE = _ws([_container("API Backend", "shop-api", [
    _component("Order Service", "shop-api-order", "api/order.py",
               relationships=[{"id": "r1", "destinationId": "shop-api-payment", "description": "calls"}]),
    _component("Payment Service", "shop-api-payment", "api/payment.py"),
])])


def _node(result, node_id):
    return next(n for n in result["nodes"] if n["id"] == node_id)


def _delta(result, node_id):
    return _node(result, node_id)["data"]["delta"]


def _decorate(base, head, level, system=None, container=None):
    return decorate(base, head, diff(base, head), level, system, container)


# --- element_paths -----------------------------------------------------------

def test_element_paths_derives_the_same_strings_the_parser_does():
    paths = element_paths(BASE["model"])
    assert paths["customer"]["path"] == "Customer"
    assert paths["shop"]["path"] == "Shop"
    assert paths["shop-api"]["path"] == "API Backend (Shop)"
    assert paths["shop-api-order"]["path"] == "Order Service (API Backend)"


def test_element_paths_keeps_a_person_and_a_system_of_one_name_distinct():
    ws = _ws([])
    ws["model"]["people"][0]["name"] = "Shop"
    paths = element_paths(ws["model"])
    assert paths["customer"]["path"] == paths["shop"]["path"] == "Shop"
    assert paths["customer"]["kind"] != paths["shop"]["kind"]


def test_element_paths_records_ancestors_for_the_rollup():
    paths = element_paths(BASE["model"])
    assert paths["shop-api-order"]["ancestors"] == ("API Backend (Shop)", "Shop")
    assert paths["shop-api"]["ancestors"] == ("Shop",)
    assert paths["shop"]["ancestors"] == ()


# --- element states ---------------------------------------------------------

def test_an_added_component_reads_as_added():
    head = _ws([_container("API Backend", "shop-api", [
        BASE["model"]["softwareSystems"][0]["containers"][0]["components"][0],
        _component("Payment Service", "shop-api-payment", "api/payment.py"),
        _component("Audit Log", "shop-api-audit", "api/audit.py"),
    ])])
    result = _decorate(BASE, head, "C3", container="shop-api")
    assert _delta(result, "shop-api-audit")["state"] == "added"
    assert _delta(result, "shop-api-payment")["state"] == "unchanged"


def test_a_modified_component_carries_its_field_rows():
    head = _ws([_container("API Backend", "shop-api", [
        _component("Order Service", "shop-api-order", "api/order.py", description="Now does more",
                   relationships=[{"id": "r1", "destinationId": "shop-api-payment", "description": "calls"}]),
        _component("Payment Service", "shop-api-payment", "api/payment.py"),
    ])])
    state = _delta(_decorate(BASE, head, "C3", container="shop-api"), "shop-api-order")
    assert state["state"] == "modified"
    assert state["self_changed"] is True
    assert [f["field"] for f in state["fields"]] == ["description"]
    assert state["fields"][0]["before"] == ""
    assert state["fields"][0]["after"] == "Now does more"


def test_an_unchanged_element_says_so_explicitly():
    state = _delta(_decorate(BASE, BASE, "C3", container="shop-api"), "shop-api-order")
    assert state == {
        "state": "unchanged", "self_changed": False, "contains_changes": False,
        "fields": [], "possible_rename_of": None,
        "ghost": False, "declared_parent": None, "relation_changed": False,
    }


def test_no_field_in_the_payload_carries_a_verdict():
    """FR-017: the view reports what changed and nothing above it."""
    head = _ws([_container("API Backend", "shop-api", [
        _component("Order Service", "shop-api-order", "api/order.py"),
    ])])
    result = _decorate(BASE, head, "C3", container="shop-api")
    forbidden = {"risk", "severity", "impact", "blast_radius", "recommendation", "verdict", "safe"}
    for carrier in [*result["nodes"], *result["edges"]]:
        assert not forbidden & set(carrier["data"]["delta"])
    assert not forbidden & set(result["summary"])


# --- ghosts -----------------------------------------------------------------

def test_a_removed_component_is_still_drawn_as_a_ghost():
    head = _ws([_container("API Backend", "shop-api", [
        BASE["model"]["softwareSystems"][0]["containers"][0]["components"][0],
    ])])
    state = _delta(_decorate(BASE, head, "C3", container="shop-api"), "shop-api-payment")
    assert state["state"] == "removed"
    assert state["ghost"] is True


def test_a_removed_container_is_a_ghost_at_c2():
    base = _ws([
        _container("API Backend", "shop-api", []),
        _container("Legacy Worker", "shop-worker", []),
    ])
    head = _ws([_container("API Backend", "shop-api", [])])
    result = _decorate(base, head, "C2", system="shop")
    assert _delta(result, "shop-worker")["state"] == "removed"


def test_a_ghost_whose_parent_is_also_gone_names_its_declared_parent():
    base = _ws([
        _container("API Backend", "shop-api", []),
        _container("Legacy Worker", "shop-worker", [_component("Job Runner", "shop-worker-job")]),
    ])
    head = _ws([_container("API Backend", "shop-api", [])])
    result = _decorate(base, head, "C2", system="shop")
    worker = _delta(result, "shop-worker")
    assert worker["state"] == "removed"
    # The component's own level is gone with its container, so C2 is where the loss is visible.
    job = next((c for c in result["summary"]["changes"] if c["path"] == "Job Runner (Legacy Worker)"), None)
    assert job is not None
    assert job["state"] == "removed"


def test_a_removed_element_keeps_its_base_id_so_saved_positions_still_apply():
    head = _ws([_container("API Backend", "shop-api", [
        BASE["model"]["softwareSystems"][0]["containers"][0]["components"][0],
    ])])
    result = _decorate(BASE, head, "C3", container="shop-api")
    assert "shop-api-payment" in {n["id"] for n in result["nodes"]}


# --- the pairing degradation ------------------------------------------------

def test_a_rename_in_a_multi_element_file_is_labelled_a_possibility_not_a_rename():
    base = _ws([_container("API Backend", "shop-api", [
        _component("Order Service", "shop-api-order", "api/services.py"),
        _component("Payment Service", "shop-api-payment", "api/services.py"),
    ])])
    head = _ws([_container("API Backend", "shop-api", [
        _component("Order Service", "shop-api-order", "api/services.py"),
        _component("Billing Service", "shop-api-billing", "api/services.py"),
    ])])
    result = _decorate(base, head, "C3", container="shop-api")
    added = _delta(result, "shop-api-billing")
    removed = _delta(result, "shop-api-payment")
    assert added["state"] == "added"
    assert added["possible_rename_of"] == "Payment Service (API Backend)"
    assert removed["possible_rename_of"] == "Billing Service (API Backend)"


# --- relations --------------------------------------------------------------

def _edge(result, source, target):
    return next(e for e in result["edges"] if e["source"] == source and e["target"] == target)


def test_a_relation_whose_description_changed_reads_as_modified():
    head = _ws([_container("API Backend", "shop-api", [
        _component("Order Service", "shop-api-order", "api/order.py",
                   relationships=[{"id": "r1", "destinationId": "shop-api-payment", "description": "charges"}]),
        _component("Payment Service", "shop-api-payment", "api/payment.py"),
    ])])
    result = _decorate(BASE, head, "C3", container="shop-api")
    state = _edge(result, "shop-api-order", "shop-api-payment")["data"]["delta"]
    assert state["state"] == "modified"
    assert [f["field"] for f in state["fields"]] == ["description"]


def test_a_removed_relation_is_still_drawn():
    head = _ws([_container("API Backend", "shop-api", [
        _component("Order Service", "shop-api-order", "api/order.py"),
        _component("Payment Service", "shop-api-payment", "api/payment.py"),
    ])])
    result = _decorate(BASE, head, "C3", container="shop-api")
    state = _edge(result, "shop-api-order", "shop-api-payment")["data"]["delta"]
    assert state["state"] == "removed"
    assert state["ghost"] is True


def test_renaming_an_endpoint_does_not_mark_its_relation_as_changed():
    head = _ws([_container("API Backend", "shop-api", [
        _component("Order Service", "shop-api-order", "api/order.py",
                   relationships=[{"id": "r1", "destinationId": "shop-api-settlement", "description": "calls"}]),
        _component("Settlement Service", "shop-api-settlement", "api/payment.py"),
    ])])
    result = _decorate(BASE, head, "C3", container="shop-api")
    state = _edge(result, "shop-api-order", "shop-api-settlement")["data"]["delta"]
    assert state["state"] == "unchanged"


# --- the containment rollup -------------------------------------------------

def test_a_container_holding_an_added_component_reads_as_modified_at_c2():
    head = _ws([_container("API Backend", "shop-api", [
        *BASE["model"]["softwareSystems"][0]["containers"][0]["components"],
        _component("Audit Log", "shop-api-audit", "api/audit.py"),
    ])])
    state = _delta(_decorate(BASE, head, "C2", system="shop"), "shop-api")
    assert state["state"] == "modified"
    assert state["contains_changes"] is True
    assert state["self_changed"] is False


def test_the_system_holding_a_changed_component_reads_as_modified_at_c1():
    head = _ws([_container("API Backend", "shop-api", [
        _component("Order Service", "shop-api-order", "api/order.py", description="changed"),
        _component("Payment Service", "shop-api-payment", "api/payment.py"),
    ])])
    state = _delta(_decorate(BASE, head, "C1"), "shop")
    assert state["state"] == "modified"
    assert state["contains_changes"] is True


def test_an_unrelated_sibling_container_stays_unchanged():
    base = _ws([
        _container("API Backend", "shop-api", [_component("Order Service", "shop-api-order")]),
        _container("Web", "shop-web", [_component("Checkout Page", "shop-web-checkout")]),
    ])
    head = _ws([
        _container("API Backend", "shop-api", [
            _component("Order Service", "shop-api-order"),
            _component("Audit Log", "shop-api-audit"),
        ]),
        _container("Web", "shop-web", [_component("Checkout Page", "shop-web-checkout")]),
    ])
    result = _decorate(base, head, "C2", system="shop")
    assert _delta(result, "shop-api")["state"] == "modified"
    assert _delta(result, "shop-web")["state"] == "unchanged"


def test_a_container_holding_both_an_addition_and_a_removal_is_modified():
    head = _ws([_container("API Backend", "shop-api", [
        BASE["model"]["softwareSystems"][0]["containers"][0]["components"][0],
        _component("Audit Log", "shop-api-audit", "api/audit.py"),
    ])])
    assert _delta(_decorate(BASE, head, "C2", system="shop"), "shop-api")["state"] == "modified"


def test_an_added_container_keeps_its_own_state_rather_than_the_rollup():
    head = _ws([
        _container("API Backend", "shop-api", BASE["model"]["softwareSystems"][0]["containers"][0]["components"]),
        _container("Reporting", "shop-reporting", [_component("Report Builder", "shop-reporting-builder")]),
    ])
    assert _delta(_decorate(BASE, head, "C2", system="shop"), "shop-reporting")["state"] == "added"


def test_the_rollup_does_not_travel_along_relations():
    """FR-010: 'this element encloses a change' is a fact; 'what it talks to is affected' is not."""
    base = _ws([
        _container("API Backend", "shop-api", [
            _component("Order Service", "shop-api-order", relationships=[
                {"id": "x1", "destinationId": "shop-web-checkout", "description": "notifies"}]),
        ]),
        _container("Web", "shop-web", [_component("Checkout Page", "shop-web-checkout")]),
    ])
    head = _ws([
        _container("API Backend", "shop-api", [
            _component("Order Service", "shop-api-order", description="changed", relationships=[
                {"id": "x1", "destinationId": "shop-web-checkout", "description": "notifies"}]),
        ]),
        _container("Web", "shop-web", [_component("Checkout Page", "shop-web-checkout")]),
    ])
    result = _decorate(base, head, "C2", system="shop")
    assert _delta(result, "shop-api")["state"] == "modified"
    assert _delta(result, "shop-web")["state"] == "unchanged"


def test_a_changed_relation_below_the_level_rolls_up_to_its_endpoints_containers():
    head = _ws([_container("API Backend", "shop-api", [
        _component("Order Service", "shop-api-order", "api/order.py",
                   relationships=[{"id": "r1", "destinationId": "shop-api-payment", "description": "charges"}]),
        _component("Payment Service", "shop-api-payment", "api/payment.py"),
    ])])
    assert _delta(_decorate(BASE, head, "C2", system="shop"), "shop-api")["contains_changes"] is True


# --- summary ----------------------------------------------------------------

def test_an_empty_delta_still_returns_the_whole_head_map():
    result = _decorate(BASE, BASE, "C3", container="shop-api")
    assert result["summary"]["empty"] is True
    assert result["summary"] == {"added": 0, "removed": 0, "changed": 0, "empty": True, "changes": []}
    assert len(result["nodes"]) == 2


def test_the_counts_include_relations_as_well_as_elements():
    head = _ws([_container("API Backend", "shop-api", [
        _component("Order Service", "shop-api-order", "api/order.py"),
        _component("Payment Service", "shop-api-payment", "api/payment.py"),
    ])])
    summary = _decorate(BASE, head, "C3", container="shop-api")["summary"]
    assert summary["removed"] == 1
    assert [c["kind"] for c in summary["changes"]] == ["relation"]


def test_the_change_list_covers_every_level_not_only_the_requested_one():
    head = _ws([
        _container("API Backend", "shop-api", [
            *BASE["model"]["softwareSystems"][0]["containers"][0]["components"],
            _component("Audit Log", "shop-api-audit", "api/audit.py"),
        ]),
        _container("Reporting", "shop-reporting", []),
    ])
    summary = _decorate(BASE, head, "C1")["summary"]
    levels = {c["level"] for c in summary["changes"]}
    assert levels == {"C2", "C3"}
    audit = next(c for c in summary["changes"] if c["path"] == "Audit Log (API Backend)")
    assert audit["node_id"] == "shop-api-audit"
    assert audit["level"] == "C3"


def test_drilling_into_a_removed_container_shows_what_it_held_rather_than_an_empty_level():
    base = _ws([
        _container("API Backend", "shop-api", []),
        _container("Legacy Worker", "shop-worker", [_component("Job Runner", "shop-worker-job")]),
    ])
    head = _ws([_container("API Backend", "shop-api", [])])
    result = _decorate(base, head, "C3", container="shop-worker")
    assert [n["id"] for n in result["nodes"]] == ["shop-worker-job"]
    assert _delta(result, "shop-worker-job")["state"] == "removed"
    assert _delta(result, "shop-worker-job")["ghost"] is True


def test_a_relation_endpoint_is_marked_so_the_rollup_does_not_dead_end():
    """A container reading 'contains changes' must have something marked inside it."""
    head = _ws([_container("API Backend", "shop-api", [
        _component("Order Service", "shop-api-order", "api/order.py",
                   relationships=[{"id": "r1", "destinationId": "shop-api-payment", "description": "now settles"}]),
        _component("Payment Service", "shop-api-payment", "api/payment.py"),
    ])])
    target = _delta(_decorate(BASE, head, "C3", container="shop-api"), "shop-api-payment")
    assert target["state"] == "modified"
    assert target["relation_changed"] is True
    assert target["self_changed"] is False
    assert target["contains_changes"] is False
