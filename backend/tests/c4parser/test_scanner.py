from pathlib import Path

from c4parser.scanner import scan
from c4parser.types import C4Component, C4Container, C4System

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


def test_scan_invalid_yaml_warns(tmp_path, capsys):
    bad = tmp_path / "bad.py"
    bad.write_text('"""\n@c1:system\nname: [bad yaml\n"""\n')
    elements = scan(str(tmp_path))
    assert elements == []
    assert "Warning:" in capsys.readouterr().err


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


def test_scan_wrong_kind_for_level_warns(tmp_path, capsys):
    bad = tmp_path / "bad.py"
    bad.write_text('"""\n@c1:container\nname: Wrong\nsystem: X\n"""\n')
    elements = scan(str(tmp_path))
    assert elements == []
    assert "must be @c1:system" in capsys.readouterr().err


def test_scan_parse_error_includes_line_number(tmp_path, capsys):
    bad = tmp_path / "bad.py"
    bad.write_text('# padding\n# padding\n"""\n@c1:system\nname: [bad yaml\n"""\n')
    elements = scan(str(tmp_path))
    assert elements == []
    assert ":3]" in capsys.readouterr().err


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


def test_c4ignore_excludes_directories(tmp_path):
    # Exact name and glob both work; patterns match relative path from root.
    (tmp_path / "generated").mkdir()
    ((tmp_path / "generated") / "auto.py").write_text('"""\n@c1:system\nname: Ghost\n"""\n')
    (tmp_path / "migrations_v2").mkdir()
    ((tmp_path / "migrations_v2") / "mod.py").write_text('"""\n@c1:system\nname: Ghost\n"""\n')
    (tmp_path / ".c4ignore").write_text("generated\nmigrations_*\n")
    assert scan(str(tmp_path)) == []


def test_c4ignore_excludes_files(tmp_path):
    # Exact filename and glob both work.
    (tmp_path / "conftest.py").write_text('"""\n@c1:system\nname: Ghost\n"""\n')
    (tmp_path / "test_views.py").write_text('"""\n@c1:system\nname: Ghost\n"""\n')
    (tmp_path / ".c4ignore").write_text("conftest.py\ntest_*.py\n")
    assert scan(str(tmp_path)) == []


def test_c4ignore_pattern_anchored_to_root(tmp_path):
    # Pattern without path only excludes the root-level match, not a nested dir with the same name.
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
