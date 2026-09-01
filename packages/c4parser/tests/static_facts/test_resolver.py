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
