from pathlib import Path

_SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build"}


def detect_package_roots(root: str) -> set[Path]:
    """Return absolute directories containing pyproject.toml or package.json,
    used to anchor import resolution — skips build/dependency directories."""
    root_path = Path(root).resolve()
    roots: set[Path] = set()
    for marker in ("pyproject.toml", "package.json"):
        for f in root_path.rglob(marker):
            # Only check path components *below* root_path, not the entire absolute path.
            # This avoids false positives when the repo is nested under a dir like /ci/build/.
            try:
                rel_parts = f.parent.relative_to(root_path).parts
                if any(part in _SKIP_DIRS for part in rel_parts):
                    continue
            except ValueError:
                # f.parent is outside root_path (shouldn't happen with rglob, but be safe)
                continue
            roots.add(f.parent.resolve())
    return roots


def resolve_python_import(raw: str, source_file: str, package_roots: set[Path]) -> str | None:
    """raw is a dotted module path, e.g. 'apps.subscriptions.manager'.
    Resolves deterministically: prefers the root that contains source_file,
    then falls back to roots sorted by path length (most specific first)."""
    parts = raw.split(".")
    source_path = Path(source_file).resolve()

    # Partition roots: ones that are ancestors of source_file first, then others.
    ancestor_roots = []
    other_roots = []
    for pkg_root in package_roots:
        try:
            source_path.relative_to(pkg_root)
            ancestor_roots.append(pkg_root)
        except ValueError:
            other_roots.append(pkg_root)

    # Sort by specificity: ancestor roots by depth (deeper first), others by path length (longer first).
    ancestor_roots.sort(key=lambda p: len(p.parts), reverse=True)
    other_roots.sort(key=lambda p: len(p.parts), reverse=True)
    sorted_roots = ancestor_roots + other_roots

    for pkg_root in sorted_roots:
        candidate = pkg_root.joinpath(*parts)
        module_file = candidate.with_suffix(".py")
        if module_file.is_file():
            return str(module_file)
        init_file = candidate / "__init__.py"
        if init_file.is_file():
            return str(init_file)
    return None


def resolve_typescript_import(raw: str, source_file: str, package_roots: set[Path]) -> str | None:
    """raw is an import source string with quotes already stripped, e.g.
    './foo' or '../bar/baz'. Bare specifiers (no leading dot) are left
    unresolved in v1 — no node_modules resolution."""
    if not raw.startswith("."):
        return None
    base = (Path(source_file).resolve().parent / raw).resolve()
    candidates = [
        base.with_suffix(".ts"), base.with_suffix(".tsx"), base.with_suffix(".js"),
        base / "index.ts", base / "index.tsx", base / "index.js",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None
