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


def test_scan_summary_line_before_marker(tmp_path):
    # Common Javadoc/docstring idiom: a summary sentence precedes the marker.
    java = tmp_path / "OrderService.java"
    java.write_text(
        "/** Order service.\n"
        " * @c3:component\n"
        " * name: Order Service\n"
        " * container: API Backend\n"
        " */\n"
        "public class OrderService {}\n"
    )
    elements = scan(str(tmp_path))
    assert len(elements) == 1
    comp = elements[0]
    assert isinstance(comp, C4Component)
    assert comp.name == "Order Service"
    assert comp.container == "API Backend"


def test_c4ignore_excludes_directory(tmp_path):
    secret = tmp_path / "generated"
    secret.mkdir()
    (secret / "auto.py").write_text('"""\n@c1:system\nname: Ghost\n"""\n')
    (tmp_path / ".c4ignore").write_text("generated\n")
    assert scan(str(tmp_path)) == []


def test_c4ignore_glob_pattern_excludes_directory(tmp_path):
    (tmp_path / "migrations_v2").mkdir()
    ((tmp_path / "migrations_v2") / "mod.py").write_text('"""\n@c1:system\nname: Ghost\n"""\n')
    (tmp_path / ".c4ignore").write_text("migrations_*\n")
    assert scan(str(tmp_path)) == []


def test_c4ignore_excludes_file(tmp_path):
    (tmp_path / "conftest.py").write_text('"""\n@c1:system\nname: Ghost\n"""\n')
    (tmp_path / ".c4ignore").write_text("conftest.py\n")
    assert scan(str(tmp_path)) == []


def test_c4ignore_glob_pattern_excludes_file(tmp_path):
    (tmp_path / "test_views.py").write_text('"""\n@c1:system\nname: Ghost\n"""\n')
    (tmp_path / ".c4ignore").write_text("test_*.py\n")
    assert scan(str(tmp_path)) == []


def test_c4ignore_name_only_does_not_match_nested_dir(tmp_path):
    # "examples" only excludes root-level examples/, NOT sub/examples/.
    nested = tmp_path / "sub" / "examples"
    nested.mkdir(parents=True)
    (nested / "mod.py").write_text('"""\n@c1:system\nname: Visible\ndescription: ok\n"""\n')
    (tmp_path / ".c4ignore").write_text("examples\n")
    elements = scan(str(tmp_path))
    assert any(getattr(e, "name", None) == "Visible" for e in elements)


def test_c4ignore_comments_and_blank_lines_ignored(tmp_path):
    (tmp_path / "real.py").write_text('"""\n@c1:system\nname: Shop\ndescription: ok\n"""\n')
    (tmp_path / ".c4ignore").write_text("# this is a comment\n\n# another comment\n")
    elements = scan(str(tmp_path))
    assert len(elements) == 1


def test_c4ignore_missing_file_is_fine(tmp_path):
    (tmp_path / "real.py").write_text('"""\n@c1:system\nname: Shop\ndescription: ok\n"""\n')
    assert not (tmp_path / ".c4ignore").exists()
    elements = scan(str(tmp_path))
    assert len(elements) == 1


def test_scan_ignores_marker_mentioned_mid_block(tmp_path):
    # A docstring or code that MENTIONS @c1: without starting with it is not
    # an annotation — the scanner must not trip on its own error messages.
    src = tmp_path / "meta.py"
    src.write_text(
        '"""\n'
        "Helper module.\n"
        "Raises an error like '@c1:system missing required field' sometimes.\n"
        '"""\n'
    )
    elements = scan(str(tmp_path))
    assert elements == []
