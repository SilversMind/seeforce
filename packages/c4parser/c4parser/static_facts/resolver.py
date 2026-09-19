from pathlib import Path

_SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build"}


def detect_package_roots(root: str) -> set[Path]:
    """Return absolute directories containing a Python or JS/TS package marker,
    used to anchor import resolution — skips build/dependency directories.
    Pipfile and setup.py are here because pyproject.toml alone missed real
    Python projects (Pipenv-based Django apps, older setuptools layouts).
    manage.py is separate and Django-specific: a Django project commonly
    nests the actual importable root (where `core`, `api`, etc. live) one
    level below the dependency-manifest file (`backend/Pipfile` vs
    `backend/signalstickers/manage.py`) — without this, imports like
    `core.services` never resolve even though Pipfile was found, because
    Pipfile's directory is the wrong root. Found running this against
    signalstickers' backend, which has exactly this layout."""
    root_path = Path(root).resolve()
    roots: set[Path] = set()
    for marker in ("pyproject.toml", "package.json", "Pipfile", "setup.py", "manage.py"):
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


def _module_file_in(base: Path, parts: list[str]) -> str | None:
    """Look for `base/parts...py` then `base/parts.../__init__.py`."""
    candidate = base.joinpath(*parts)
    if parts:
        module_file = candidate.with_suffix(".py")
        if module_file.is_file():
            return str(module_file)
    init_file = candidate / "__init__.py"
    if init_file.is_file():
        return str(init_file)
    return None


def _resolve_relative_python_import(raw: str, source_path: Path) -> str | None:
    """raw is a relative import with leading dots, e.g. '.', '.types', '..pkg.mod'.
    One dot means the source file's own package (its directory); each extra dot
    walks one directory further up. Whatever follows the dots is a dotted path
    resolved from there."""
    dots = len(raw) - len(raw.lstrip("."))
    rest = raw[dots:]

    base = source_path.parent
    for _ in range(dots - 1):
        base = base.parent

    return _module_file_in(base, rest.split(".") if rest else [])


def resolve_python_import(raw: str, source_file: str, package_roots: set[Path]) -> str | None:
    """raw is a dotted module path, e.g. 'apps.subscriptions.manager', or a
    relative one, e.g. '.types' / '..pkg.mod'.

    Absolute paths resolve deterministically: the root containing source_file
    wins, then remaining roots sorted by depth (deepest first) with an
    alphabetical tiebreak. The source file's own directory is tried last, as an
    implicit root — flat script directories (no pyproject.toml/package.json
    anywhere above them) import their siblings by bare name and would otherwise
    never resolve."""
    source_path = Path(source_file).resolve()

    if raw.startswith("."):
        return _resolve_relative_python_import(raw, source_path)

    parts = raw.split(".")

    # Partition roots: ones that are ancestors of source_file first, then others.
    ancestor_roots = []
    other_roots = []
    for pkg_root in package_roots:
        try:
            source_path.relative_to(pkg_root)
            ancestor_roots.append(pkg_root)
        except ValueError:
            other_roots.append(pkg_root)

    # Sort by specificity: ancestor roots by depth (deeper first), others by path length (longer first),
    # with alphabetical path tiebreak to ensure full determinism regardless of hash seed.
    ancestor_roots.sort(key=lambda p: (-len(p.parts), str(p)))
    other_roots.sort(key=lambda p: (-len(p.parts), str(p)))
    sorted_roots = ancestor_roots + other_roots

    # Implicit last-resort root: the importing file's own directory. Appended
    # after the real roots so declared packages always win — this only rescues
    # imports nothing else could resolve, keeping the ordering above intact.
    own_dir = source_path.parent
    if own_dir not in sorted_roots:
        sorted_roots.append(own_dir)

    for pkg_root in sorted_roots:
        resolved = _module_file_in(pkg_root, parts)
        if resolved is not None:
            return resolved
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
