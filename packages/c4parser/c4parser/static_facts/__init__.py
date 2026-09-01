"""
@c3:component
name: Static Facts Extractor
container: Annotation Parser
technology: tree-sitter
description: Statically extracts imports, top-level definitions, and adjacent docstrings from source files (Python, TypeScript) as an unverified candidate signal — never a source of truth. Isolated in its own subpackage behind extract_facts() so tree-sitter (an optional dependency) can be dropped without breaking annotation scanning or building.
"""
import importlib.util
from pathlib import Path

from . import noise, resolver
from .types import DefFact, FileFacts, ImportFact

__all__ = ["extract_facts", "FileFacts", "ImportFact", "DefFact"]

_EXT_LANGUAGE = {".py": "python", ".ts": "typescript", ".tsx": "typescript"}


def _backend_available() -> bool:
    return importlib.util.find_spec("tree_sitter_language_pack") is not None


def extract_facts(root: str, files: list[str]) -> list[FileFacts]:
    """
    Given a repo root and a list of file paths, return statically-extracted
    candidate facts for each recognized (Python/TypeScript) file. Returns []
    if the optional `static-facts` extra isn't installed, or if `files` is
    empty. Never raises on a per-file parse error — that file is skipped.
    """
    if not _backend_available() or not files:
        return []

    from . import backend  # local import: only touches tree-sitter once we know it's installed

    package_roots = resolver.detect_package_roots(root)
    results: list[FileFacts] = []

    for file_path in files:
        language = _EXT_LANGUAGE.get(Path(file_path).suffix)
        if language is None:
            continue
        try:
            source = Path(file_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        try:
            if language == "python":
                raw_imports, defines = backend.extract_python(file_path, source)
            else:
                raw_imports, defines = backend.extract_typescript(file_path, source)
        except Exception:
            continue  # malformed syntax — skip this file, keep going

        kept_imports: list[ImportFact] = []
        for raw in raw_imports:
            if language == "python":
                resolved = resolver.resolve_python_import(raw, file_path, package_roots)
            else:
                resolved = resolver.resolve_typescript_import(raw, file_path, package_roots)

            if resolved is not None:
                kept_imports.append(ImportFact(raw=raw, resolved_path=resolved, kind="internal"))
                continue

            top = noise.top_level_name(raw, language)
            if noise.is_known_external(top, language):
                kept_imports.append(ImportFact(raw=raw, resolved_path=None, kind="external_known"))
            # else: stdlib or unknown generic — dropped as noise

        results.append(FileFacts(file=file_path, imports=kept_imports, defines=defines))

    return results
