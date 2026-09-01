from pathlib import Path

from c4parser.static_facts import resolver


def test_detect_package_roots_finds_pyproject(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "pyproject.toml").write_text("[project]\nname='x'\n")
    roots = resolver.detect_package_roots(str(tmp_path))
    assert (tmp_path / "pkg").resolve() in roots


def test_detect_package_roots_skips_venv(tmp_path):
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "pyproject.toml").write_text("[project]\nname='x'\n")
    roots = resolver.detect_package_roots(str(tmp_path))
    assert not any(".venv" in str(r) for r in roots)


def test_resolve_python_import_finds_module_file(tmp_path):
    pkg = tmp_path / "apps" / "subscriptions"
    pkg.mkdir(parents=True)
    (pkg / "manager.py").write_text("")
    resolved = resolver.resolve_python_import(
        "apps.subscriptions.manager", str(tmp_path / "caller.py"), {tmp_path}
    )
    assert resolved == str(pkg / "manager.py")


def test_resolve_python_import_finds_package_init(tmp_path):
    pkg = tmp_path / "apps" / "subscriptions"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    resolved = resolver.resolve_python_import(
        "apps.subscriptions", str(tmp_path / "caller.py"), {tmp_path}
    )
    assert resolved == str(pkg / "__init__.py")


def test_resolve_python_import_unresolved_returns_none():
    resolved = resolver.resolve_python_import("nonexistent.module", "caller.py", set())
    assert resolved is None


def test_resolve_typescript_import_relative(tmp_path):
    (tmp_path / "util.ts").write_text("")
    resolved = resolver.resolve_typescript_import(
        "./util", str(tmp_path / "index.ts"), set()
    )
    assert resolved == str(tmp_path / "util.ts")


def test_resolve_typescript_import_bare_specifier_unresolved():
    resolved = resolver.resolve_typescript_import("axios", "index.ts", set())
    assert resolved is None


def test_detect_package_roots_skips_only_relative_skip_dirs(tmp_path):
    """Verify that detect_package_roots skips skip-dirs only below root_path,
    not in parent directories. E.g., /ci/build/repo/ should still find packages."""
    # Simulate a root path containing a skip-dir-like name
    root_with_skip_name = tmp_path / "build" / "dist" / "src"
    root_with_skip_name.mkdir(parents=True)
    (root_with_skip_name / "app").mkdir()
    (root_with_skip_name / "app" / "pyproject.toml").write_text("[project]\nname='x'\n")

    # Also add a skip-dir below the root that should be skipped
    (root_with_skip_name / ".venv" / "lib").mkdir(parents=True)
    (root_with_skip_name / ".venv" / "lib" / "pyproject.toml").write_text("[project]\nname='y'\n")

    roots = resolver.detect_package_roots(str(root_with_skip_name))
    # Should find the app package (not skipped even though root has "build" and "dist")
    assert (root_with_skip_name / "app").resolve() in roots
    # Should NOT find the .venv package (skipped)
    assert not any(".venv" in str(r) for r in roots)


def test_resolve_python_import_multi_root_deterministic(tmp_path):
    """Verify that resolve_python_import returns deterministically when multiple
    roots match, preferring the root that contains source_file."""
    # Create two package roots
    root1 = tmp_path / "monorepo1"
    root2 = tmp_path / "monorepo2"
    root1.mkdir()
    root2.mkdir()

    # Both have the same module
    for root in [root1, root2]:
        (root / "shared").mkdir()
        (root / "shared" / "utils.py").write_text("")

    # Source file is in root1, so resolution should prefer root1
    source_file = str(root1 / "caller.py")
    roots = {root1, root2}

    # Call multiple times to verify deterministic order (would fail randomly with set order)
    results = [
        resolver.resolve_python_import("shared.utils", source_file, roots)
        for _ in range(5)
    ]
    # All results should be the same
    assert all(r == results[0] for r in results)
    # Should prefer root1 since source_file is in root1
    assert results[0] == str(root1 / "shared" / "utils.py")


def test_resolve_python_import_equal_depth_roots_deterministic(tmp_path):
    """Verify that resolve_python_import returns deterministically when two
    non-ancestor roots have equal depth and both contain the matching module.
    Should sort alphabetically by path as tiebreaker (not by hash order)."""
    # Create two sibling package roots at same depth
    root_a = tmp_path / "services" / "auth"
    root_b = tmp_path / "services" / "billing"
    root_a.mkdir(parents=True)
    root_b.mkdir(parents=True)

    # Both have the same module
    for root in [root_a, root_b]:
        (root / "config").mkdir()
        (root / "config" / "settings.py").write_text("")

    # Source file is outside both roots
    source_file = str(tmp_path / "outside" / "caller.py")
    roots = {root_a, root_b}

    # Both roots have same depth (len(parts)), so tiebreak should be alphabetical.
    # root_a comes before root_b alphabetically, so should always win.
    result = resolver.resolve_python_import("config.settings", source_file, roots)
    assert result == str(root_a / "config" / "settings.py")


# --- relative imports (from . import x / from .mod import y / from ..pkg import z) ---


def test_resolve_python_relative_import_bare_dot_finds_own_package_init(tmp_path):
    """`from . import x` targets the source file's own package __init__.py."""
    pkg = tmp_path / "apps" / "subscriptions"
    pkg.mkdir(parents=True)
    init_file = pkg / "__init__.py"
    init_file.write_text("")
    resolved = resolver.resolve_python_import(".", str(pkg / "manager.py"), {tmp_path})
    assert resolved == str(init_file)


def test_resolve_python_relative_import_sibling_module(tmp_path):
    """`from .sibling import y` targets sibling.py next to the source file."""
    pkg = tmp_path / "apps" / "subscriptions"
    pkg.mkdir(parents=True)
    sibling = pkg / "sibling.py"
    sibling.write_text("")
    resolved = resolver.resolve_python_import(
        ".sibling", str(pkg / "manager.py"), {tmp_path}
    )
    assert resolved == str(sibling)


def test_resolve_python_relative_import_parent_package_dotted(tmp_path):
    """`from ..pkg.mod import z` walks one directory up, then down pkg/mod.py."""
    base = tmp_path / "apps"
    (base / "subscriptions").mkdir(parents=True)
    (base / "pkg").mkdir()
    target = base / "pkg" / "mod.py"
    target.write_text("")
    resolved = resolver.resolve_python_import(
        "..pkg.mod", str(base / "subscriptions" / "manager.py"), {tmp_path}
    )
    assert resolved == str(target)


def test_resolve_python_relative_import_sibling_package_init(tmp_path):
    """`from ..sibling import z` resolves a sibling *package* via its __init__.py."""
    base = tmp_path / "apps"
    (base / "subscriptions").mkdir(parents=True)
    (base / "sibling").mkdir()
    init_file = base / "sibling" / "__init__.py"
    init_file.write_text("")
    resolved = resolver.resolve_python_import(
        "..sibling", str(base / "subscriptions" / "manager.py"), {tmp_path}
    )
    assert resolved == str(init_file)


def test_resolve_python_relative_import_unresolvable_returns_none(tmp_path):
    pkg = tmp_path / "apps"
    pkg.mkdir()
    resolved = resolver.resolve_python_import(
        ".nope", str(pkg / "manager.py"), {tmp_path}
    )
    assert resolved is None


# --- same-directory flat sibling imports (no pyproject.toml anywhere above) ---


def test_resolve_python_import_flat_sibling_without_package_root(tmp_path):
    """A script directory with no pyproject.toml above it (this repo's own mcp/*.py)
    still resolves `from client import x` against its own directory."""
    scripts = tmp_path / "mcp"
    scripts.mkdir()
    sibling = scripts / "client.py"
    sibling.write_text("")
    resolved = resolver.resolve_python_import(
        "client", str(scripts / "server.py"), set()
    )
    assert resolved == str(sibling)


def test_resolve_python_import_flat_sibling_package_dir(tmp_path):
    """Same fallback resolves a sibling package directory via its __init__.py."""
    scripts = tmp_path / "mcp"
    (scripts / "static_facts").mkdir(parents=True)
    init_file = scripts / "static_facts" / "__init__.py"
    init_file.write_text("")
    resolved = resolver.resolve_python_import(
        "static_facts", str(scripts / "server.py"), set()
    )
    assert resolved == str(init_file)


def test_resolve_python_import_own_dir_fallback_loses_to_package_roots(tmp_path):
    """The own-directory fallback is a last resort: a real package root that also
    matches still wins, so the Task 3 ancestor-preference ordering is unchanged."""
    root = tmp_path / "repo"
    (root / "shared").mkdir(parents=True)
    root_target = root / "shared" / "utils.py"
    root_target.write_text("")

    caller_dir = root / "apps"
    caller_dir.mkdir()
    # A same-named decoy right next to the caller — must NOT win over the package root.
    (caller_dir / "shared").mkdir()
    (caller_dir / "shared" / "utils.py").write_text("")

    resolved = resolver.resolve_python_import(
        "shared.utils", str(caller_dir / "service.py"), {root}
    )
    assert resolved == str(root_target)
