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
