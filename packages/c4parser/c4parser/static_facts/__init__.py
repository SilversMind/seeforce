"""
@c3:component
name: Static Facts Extractor
container: Annotation Parser
technology: tree-sitter
description: Statically extracts imports, top-level definitions, and adjacent docstrings from source files (Python, TypeScript) as an unverified candidate signal — never a source of truth. Isolated in its own subpackage behind extract_facts() so tree-sitter (an optional dependency) can be dropped without breaking annotation scanning or building.
"""
import importlib.util

from .types import DefFact, FileFacts, ImportFact

__all__ = ["extract_facts", "FileFacts", "ImportFact", "DefFact"]


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
    return []  # filled in by Task 6
