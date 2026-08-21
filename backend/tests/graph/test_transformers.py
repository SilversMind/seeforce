import pytest
from apps.graph.transformers import to_react_flow

WORKSPACE = {
    "name": "Shop",
    "model": {
        "people": [{"id": "customer", "name": "Customer", "relationships": [
            {"id": "r1", "destinationId": "shop", "description": "Uses"}
        ]}],
        "softwareSystems": [
            {
                "id": "shop", "name": "Shop", "description": "E-commerce",
                "tags": "Element,Software System",
                "relationships": [],
                "containers": [
                    {
                        "id": "shop-api", "name": "API Backend", "technology": "Django",
                        "description": "", "tags": "Element,Container",
                        "relationships": [],
                        "components": [
                            {
                                "id": "shop-api-order", "name": "Order Service",
                                "technology": "Django", "description": "",
                                "tags": "Element,Component",
                                "relationships": [
                                    {"id": "r2", "destinationId": "shop-api-payment", "description": "calls"}
                                ],
                            },
                            {
                                "id": "shop-api-payment", "name": "Payment Service",
                                "technology": "Django", "description": "",
                                "tags": "Element,Component",
                                "relationships": [],
                            },
                        ],
                    }
                ],
            }
        ],
    },
    "views": {
        "systemContextViews": [{"key": "SystemContext", "softwareSystemId": "shop"}],
        "containerViews": [{"key": "Containers-shop", "softwareSystemId": "shop"}],
        "componentViews": [{"key": "Components-shop-api", "containerId": "shop-api"}],
        "configuration": {"styles": {"elements": [], "relationships": []}},
    },
}


def test_c1_view_returns_system_and_person_nodes():
    result = to_react_flow(WORKSPACE, level="C1", system=None, container=None)
    node_types = {n["type"] for n in result["nodes"]}
    assert "system" in node_types
    assert "person" in node_types


def test_c1_view_returns_edges():
    result = to_react_flow(WORKSPACE, level="C1", system=None, container=None)
    assert len(result["edges"]) >= 1
    assert result["edges"][0]["source"] == "customer"
    assert result["edges"][0]["target"] == "shop"


def test_c2_view_returns_container_nodes():
    result = to_react_flow(WORKSPACE, level="C2", system="shop", container=None)
    node_types = {n["type"] for n in result["nodes"]}
    assert "container" in node_types
    assert len(result["nodes"]) == 1


def test_c3_view_returns_component_nodes():
    result = to_react_flow(WORKSPACE, level="C3", system=None, container="shop-api")
    node_types = {n["type"] for n in result["nodes"]}
    assert "component" in node_types
    assert len(result["nodes"]) == 2


def test_c3_view_returns_edges():
    result = to_react_flow(WORKSPACE, level="C3", system=None, container="shop-api")
    assert len(result["edges"]) == 1
    assert result["edges"][0]["source"] == "shop-api-order"
    assert result["edges"][0]["target"] == "shop-api-payment"


def test_unknown_level_returns_empty():
    result = to_react_flow(WORKSPACE, level="C4", system=None, container=None)
    assert result == {"nodes": [], "edges": []}


def test_nodes_get_distinct_grid_positions():
    for level, system, container in [("C1", None, None), ("C3", None, "shop-api")]:
        result = to_react_flow(WORKSPACE, level=level, system=system, container=container)
        positions = [(n["position"]["x"], n["position"]["y"]) for n in result["nodes"]]
        assert len(result["nodes"]) > 1
        assert len(set(positions)) == len(positions)


def test_grid_positions_are_deterministic():
    first = to_react_flow(WORKSPACE, level="C3", system=None, container="shop-api")
    second = to_react_flow(WORKSPACE, level="C3", system=None, container="shop-api")
    assert first == second


WORKSPACE_WITH_EXTERNAL = {
    "name": "Shop",
    "model": {
        "people": [],
        "softwareSystems": [
            {
                "id": "shop", "name": "Shop", "description": "",
                "tags": "Element,Software System",
                "relationships": [
                    {"id": "r-sys", "destinationId": "kafka-order-events", "description": ""}
                ],
                "containers": [
                    {
                        "id": "shop-api", "name": "API Backend", "technology": "Django",
                        "description": "", "tags": "Element,Container",
                        "relationships": [
                            {"id": "r-cont", "destinationId": "kafka-order-events", "description": "publishes"}
                        ],
                        "components": [
                            {
                                "id": "shop-api-order", "name": "Order Service",
                                "technology": "", "description": "",
                                "tags": "Element,Component",
                                "relationships": [
                                    {"id": "r-comp-ext", "destinationId": "kafka-order-events", "description": ""},
                                    {"id": "r-comp-cross", "destinationId": "shop-auth-tokens", "description": ""},
                                ],
                            },
                        ],
                    },
                    {
                        "id": "shop-auth", "name": "Auth Service", "technology": "",
                        "description": "", "tags": "Element,Container",
                        "relationships": [],
                        "components": [
                            {
                                "id": "shop-auth-tokens", "name": "Token Validator",
                                "technology": "", "description": "",
                                "tags": "Element,Component",
                                "relationships": [],
                            },
                        ],
                    },
                ],
            },
            {
                "id": "kafka-order-events", "name": "kafka:order-events",
                "description": "", "tags": "Element,Software System,External",
                "relationships": [], "containers": [],
            },
        ],
    },
    "views": {},
}


def test_c2_view_emits_placeholder_for_external_target():
    result = to_react_flow(WORKSPACE_WITH_EXTERNAL, level="C2", system="shop", container=None)
    nodes = {n["id"]: n for n in result["nodes"]}
    assert "kafka-order-events" in nodes
    assert nodes["kafka-order-events"]["type"] == "external"
    assert nodes["kafka-order-events"]["data"]["label"] == "kafka:order-events"
    assert any(e["target"] == "kafka-order-events" for e in result["edges"])


def test_c3_view_emits_placeholders_for_external_and_cross_container_targets():
    result = to_react_flow(WORKSPACE_WITH_EXTERNAL, level="C3", system=None, container="shop-api")
    nodes = {n["id"]: n for n in result["nodes"]}
    assert nodes["kafka-order-events"]["type"] == "external"
    assert nodes["kafka-order-events"]["data"]["label"] == "kafka:order-events"
    assert "nav" not in nodes["kafka-order-events"]["data"]
    # A component in a sibling container is a real internal element, not a
    # true C1 external — it must render as its own kind (so ComponentNode
    # picks it up, not ExternalNode) and carry a nav target to jump to it.
    assert nodes["shop-auth-tokens"]["type"] == "component"
    assert nodes["shop-auth-tokens"]["data"]["label"] == "Token Validator"
    assert nodes["shop-auth-tokens"]["data"]["nav"] == {
        "level": "C3",
        "systemId": "shop",
        "systemName": "Shop",
        "containerId": "shop-auth",
        "containerName": "Auth Service",
    }
    edge_targets = {e["target"] for e in result["edges"]}
    assert {"kafka-order-events", "shop-auth-tokens"} <= edge_targets


def test_c1_view_includes_system_relationship_edges():
    result = to_react_flow(WORKSPACE_WITH_EXTERNAL, level="C1", system=None, container=None)
    assert {"shop", "kafka-order-events"} <= {n["id"] for n in result["nodes"]}
    assert any(
        e["source"] == "shop" and e["target"] == "kafka-order-events"
        for e in result["edges"]
    )
