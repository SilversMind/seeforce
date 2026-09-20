import pytest
from c4parser.types import C4System, C4Container, C4Component
from c4parser.builder import build
from c4parser.exceptions import C4ValidationError


def _make_elements():
    return [
        C4System(name="Shop", description="E-commerce"),
        C4Container(name="API Backend", system="Shop", technology="Django"),
        C4Component(name="Order Service", container="API Backend", uses=["Payment Service"]),
        C4Component(name="Payment Service", container="API Backend"),
    ]


def test_build_produces_software_system():
    workspace = build(_make_elements())
    systems = workspace["model"]["softwareSystems"]
    assert len(systems) == 1
    assert systems[0]["name"] == "Shop"
    assert systems[0]["id"] == "shop"


def test_build_produces_container():
    workspace = build(_make_elements())
    containers = workspace["model"]["softwareSystems"][0]["containers"]
    assert len(containers) == 1
    assert containers[0]["name"] == "API Backend"
    assert containers[0]["technology"] == "Django"


def test_build_produces_components():
    workspace = build(_make_elements())
    components = workspace["model"]["softwareSystems"][0]["containers"][0]["components"]
    names = {c["name"] for c in components}
    assert names == {"Order Service", "Payment Service"}


def test_build_resolves_uses_relationship():
    workspace = build(_make_elements())
    components = workspace["model"]["softwareSystems"][0]["containers"][0]["components"]
    order = next(c for c in components if c["name"] == "Order Service")
    assert len(order["relationships"]) == 1
    # Component ID: {slug(system)}-{slug(container)}-{slug(component)}
    # => shop-api-backend-payment-service
    assert order["relationships"][0]["destinationId"] == "shop-api-backend-payment-service"


def test_build_broker_uses_creates_external_system():
    elements = [
        C4System(name="Shop"),
        C4Container(name="API Backend", system="Shop"),
        C4Component(name="Order Service", container="API Backend", uses=["kafka:order-events"]),
    ]
    workspace = build(elements)
    systems = workspace["model"]["softwareSystems"]
    external = next((s for s in systems if s.get("tags", "").find("External") >= 0), None)
    assert external is not None
    assert external["name"] == "kafka:order-events"


def test_build_missing_system_for_container_raises():
    elements = [C4Container(name="Orphan", system="NonExistent")]
    with pytest.raises(C4ValidationError):
        build(elements)


def test_build_missing_container_for_component_raises():
    elements = [
        C4System(name="Shop"),
        C4Component(name="Orphan", container="NonExistent"),
    ]
    with pytest.raises(C4ValidationError):
        build(elements)


def test_build_produces_views():
    workspace = build(_make_elements())
    assert len(workspace["views"]["systemContextViews"]) == 1
    assert len(workspace["views"]["containerViews"]) == 1
    assert len(workspace["views"]["componentViews"]) == 1


# --- Tests for Correction 2: enhanced uses resolution ---

def test_build_qualified_cross_container_reference_resolves():
    """ContainerName/ComponentName qualified ref resolves to the correct container."""
    elements = [
        C4System(name="Shop"),
        C4Container(name="API Backend", system="Shop"),
        C4Container(name="Auth Service", system="Shop"),
        C4Component(name="Order Service", container="API Backend",
                    uses=["Auth Service/Token Validator"]),
        C4Component(name="Token Validator", container="Auth Service"),
    ]
    workspace = build(elements)
    # Find Order Service
    systems = workspace["model"]["softwareSystems"]
    shop = systems[0]
    api_backend = next(c for c in shop["containers"] if c["name"] == "API Backend")
    order = next(c for c in api_backend["components"] if c["name"] == "Order Service")
    assert len(order["relationships"]) == 1
    # Token Validator is in Auth Service container: shop-auth-service-token-validator
    assert order["relationships"][0]["destinationId"] == "shop-auth-service-token-validator"


def test_build_same_name_components_in_different_containers_resolve_locally():
    """Two components with the same name in different containers resolve locally."""
    elements = [
        C4System(name="Shop"),
        C4Container(name="API Backend", system="Shop"),
        C4Container(name="Auth Service", system="Shop"),
        # Both containers have a "Logger" component
        C4Component(name="Logger", container="API Backend"),
        C4Component(name="Logger", container="Auth Service"),
        # "API Client" in API Backend uses "Logger" — should resolve to the local one
        C4Component(name="API Client", container="API Backend", uses=["Logger"]),
    ]
    workspace = build(elements)
    shop = workspace["model"]["softwareSystems"][0]
    api_backend = next(c for c in shop["containers"] if c["name"] == "API Backend")
    api_client = next(c for c in api_backend["components"] if c["name"] == "API Client")
    assert len(api_client["relationships"]) == 1
    # Should resolve to Logger in API Backend: shop-api-backend-logger
    assert api_client["relationships"][0]["destinationId"] == "shop-api-backend-logger"


def test_build_ambiguous_unqualified_cross_container_reference_raises():
    """Unqualified name that matches components in two different containers raises C4ValidationError."""
    elements = [
        C4System(name="Shop"),
        C4Container(name="API Backend", system="Shop"),
        C4Container(name="Auth Service", system="Shop"),
        C4Container(name="Billing", system="Shop"),
        # "Worker" exists in two OTHER containers (not where source lives)
        C4Component(name="Worker", container="API Backend"),
        C4Component(name="Worker", container="Auth Service"),
        # Source in Billing tries to use "Worker" unqualified — ambiguous
        C4Component(name="Dispatcher", container="Billing", uses=["Worker"]),
    ]
    with pytest.raises(C4ValidationError):
        build(elements)


def test_build_container_broker_uses_creates_external_system():
    elements = [
        C4System(name="Shop"),
        C4Container(name="API Backend", system="Shop", uses=["kafka:order-events"]),
    ]
    workspace = build(elements)
    systems = workspace["model"]["softwareSystems"]
    external = next((s for s in systems if "External" in s.get("tags", "")), None)
    assert external is not None
    assert external["id"] == "kafka-order-events"
    container = systems[0]["containers"][0]
    assert container["relationships"][0]["destinationId"] == "kafka-order-events"


def test_build_rolls_up_cross_system_relationships_to_c1():
    elements = [
        C4System(name="Shop"),
        C4System(name="Warehouse"),
        C4Container(name="API Backend", system="Shop", uses=["Warehouse"]),
        C4Component(name="Order Service", container="API Backend",
                    uses=["kafka:order-events"]),
    ]
    workspace = build(elements)
    shop = next(s for s in workspace["model"]["softwareSystems"] if s["id"] == "shop")
    destinations = {r["destinationId"] for r in shop["relationships"]}
    assert destinations == {"warehouse", "kafka-order-events"}


def test_build_rollup_deduplicates_and_skips_intra_system_uses():
    elements = [
        C4System(name="Shop"),
        C4Container(name="API Backend", system="Shop"),
        C4Component(name="Order Service", container="API Backend",
                    uses=["Payment Service", "kafka:order-events"]),
        C4Component(name="Payment Service", container="API Backend",
                    uses=["kafka:order-events"]),
    ]
    workspace = build(elements)
    shop = next(s for s in workspace["model"]["softwareSystems"] if s["id"] == "shop")
    destinations = [r["destinationId"] for r in shop["relationships"]]
    assert destinations == ["kafka-order-events"]


def test_build_rollup_carries_description_from_child_relationship():
    """The C1 edge shouldn't be left blank -- it should say how the systems
    interact, using the description(s) from the crossing container/component
    uses:, joined when more than one container gives a distinct reason."""
    elements = [
        C4System(name="Shop"),
        C4System(name="Warehouse", external=True),
        C4Container(
            name="API Backend", system="Shop",
            uses=[{"Warehouse": "pulls stock levels"}],
        ),
        C4Container(
            name="Fulfillment Worker", system="Shop",
            uses=[{"Warehouse": "pushes shipped order events"}],
        ),
    ]
    workspace = build(elements)
    shop = next(s for s in workspace["model"]["softwareSystems"] if s["id"] == "shop")
    rel = next(r for r in shop["relationships"] if r["destinationId"] == "warehouse")
    assert rel["description"] == "pulls stock levels; pushes shipped order events"


def test_build_qualified_reference_missing_raises():
    """Qualified ContainerName/ComponentName where component doesn't exist raises C4ValidationError."""
    elements = [
        C4System(name="Shop"),
        C4Container(name="API Backend", system="Shop"),
        C4Container(name="Auth Service", system="Shop"),
        C4Component(name="Order Service", container="API Backend",
                    uses=["Auth Service/NonExistent"]),
    ]
    with pytest.raises(C4ValidationError):
        build(elements)


def test_build_names_workspace_after_non_external_system():
    """The primary/workspace-naming system must be the product under
    documentation, not whichever @c1:system happened to be scanned first."""
    elements = [
        C4System(name="Stripe", external=True),
        C4System(name="Shop"),
        C4Container(name="API Backend", system="Shop"),
    ]
    workspace = build(elements)
    assert workspace["name"] == "Shop"
    assert workspace["views"]["systemContextViews"][0]["softwareSystemId"] == "shop"


def test_build_allows_same_target_with_different_technology():
    """Two uses: entries naming the same target are fine when a technology:
    field distinguishes them (e.g. REST vs WebSocket, per the documented
    Edge Technology Field pattern) -- only a true same-name-same-technology
    duplicate should raise."""
    elements = [
        C4System(name="Shop"),
        C4Container(name="API Server", system="Shop"),
        C4Container(
            name="Web App",
            system="Shop",
            uses=[
                {"API Server": "authenticates users", "technology": "REST"},
                {"API Server": "receives live events", "technology": "WebSocket"},
            ],
        ),
    ]
    workspace = build(elements)
    web_app = next(c for c in workspace["model"]["softwareSystems"][0]["containers"] if c["name"] == "Web App")
    assert len(web_app["relationships"]) == 2
    technologies = {r["technology"] for r in web_app["relationships"]}
    assert technologies == {"REST", "WebSocket"}


def test_build_rejects_true_duplicate_uses_target():
    """Same target, same (empty) technology, listed twice -- still an error."""
    elements = [
        C4System(name="Shop"),
        C4Container(name="API Backend", system="Shop", uses=["Database", "Database"]),
        C4Container(name="Database", system="Shop"),
    ]
    with pytest.raises(C4ValidationError):
        build(elements)
