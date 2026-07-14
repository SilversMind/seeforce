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
