import pytest
from pathlib import Path
from c4parser.scanner import scan
from c4parser.types import C4System, C4Container, C4Component
from c4parser.exceptions import C4ParseError

FIXTURES = Path(__file__).parent / "fixtures" / "sample_project"


def test_scan_finds_system():
    elements = scan(str(FIXTURES))
    systems = [e for e in elements if isinstance(e, C4System)]
    assert len(systems) == 1
    assert systems[0].name == "Shop"
    assert systems[0].description == "E-commerce platform"


def test_scan_finds_container():
    elements = scan(str(FIXTURES))
    containers = [e for e in elements if isinstance(e, C4Container)]
    assert len(containers) == 1
    assert containers[0].name == "API Backend"
    assert containers[0].system == "Shop"
    assert containers[0].technology == "Python/Django"


def test_scan_finds_components():
    elements = scan(str(FIXTURES))
    components = [e for e in elements if isinstance(e, C4Component)]
    assert len(components) == 2
    names = {c.name for c in components}
    assert names == {"Order Service", "Payment Service"}


def test_scan_component_uses():
    elements = scan(str(FIXTURES))
    order = next(c for c in elements if isinstance(c, C4Component) and c.name == "Order Service")
    assert "Payment Service" in order.uses
    assert "kafka:order-events" in order.uses


def test_scan_records_source_file():
    elements = scan(str(FIXTURES))
    order = next(c for c in elements if isinstance(c, C4Component) and c.name == "Order Service")
    assert "services.py" in order.source_file


def test_scan_skips_pycache(tmp_path):
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "module.py").write_text('"""\n@c1:system\nname: Ghost\n"""\n')
    elements = scan(str(tmp_path))
    assert not any(getattr(e, "name", None) == "Ghost" for e in elements)


def test_scan_invalid_yaml_raises(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text('"""\n@c1:system\nname: [bad yaml\n"""\n')
    with pytest.raises(C4ParseError):
        scan(str(tmp_path))


def test_scan_java_block_comment(tmp_path):
    java = tmp_path / "OrderService.java"
    java.write_text(
        "/**\n"
        " * @c3:component\n"
        " * name: Order Service\n"
        " * container: API Backend\n"
        " * technology: Java/Spring\n"
        " * uses:\n"
        " *   - Payment Service\n"
        " */\n"
        "public class OrderService {}\n"
    )
    elements = scan(str(tmp_path))
    assert len(elements) == 1
    comp = elements[0]
    assert isinstance(comp, C4Component)
    assert comp.name == "Order Service"
    assert comp.technology == "Java/Spring"
    assert comp.uses == ["Payment Service"]


def test_scan_wrong_kind_for_level_raises(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text('"""\n@c1:container\nname: Wrong\nsystem: X\n"""\n')
    with pytest.raises(C4ParseError) as exc_info:
        scan(str(tmp_path))
    assert "must be @c1:system" in str(exc_info.value)


def test_scan_parse_error_includes_line_number(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text('# padding\n# padding\n"""\n@c1:system\nname: [bad yaml\n"""\n')
    with pytest.raises(C4ParseError) as exc_info:
        scan(str(tmp_path))
    assert exc_info.value.line == 3
