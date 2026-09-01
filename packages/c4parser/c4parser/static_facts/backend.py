from pathlib import Path

import tree_sitter
from tree_sitter_language_pack import get_language, get_parser

from .types import DefFact

_QUERIES_DIR = Path(__file__).parent / "queries"
_PYTHON_QUERY = (_QUERIES_DIR / "python.scm").read_text()


def _node_text(node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")


def _python_docstring(def_node, source_bytes: bytes) -> str:
    body = def_node.child_by_field_name("body")
    if body is None or body.child_count == 0:
        return ""
    first = body.children[0]
    # Older tree-sitter-python grammars wrap the docstring in an
    # expression_statement; newer ones put the string node directly as the
    # first statement in the block. Handle both shapes.
    if first.type == "expression_statement" and first.child_count > 0:
        first = first.children[0]
    if first.type != "string":
        return ""
    content_node = next((c for c in first.children if c.type == "string_content"), None)
    if content_node is not None:
        return _node_text(content_node, source_bytes).strip()
    return _node_text(first, source_bytes).strip("\"' \n\t")


def extract_python(file_path: str, source: str) -> tuple[list[str], list[DefFact]]:
    parser = get_parser("python")
    language = get_language("python")
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)

    query = tree_sitter.Query(language, _PYTHON_QUERY)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node)

    imports = [_node_text(n, source_bytes) for n in captures.get("import", [])]

    defines: list[DefFact] = []
    for node in captures.get("def", []):
        name_node = node.child_by_field_name("name")
        name = _node_text(name_node, source_bytes) if name_node else ""
        kind = "class" if node.type == "class_definition" else "function"
        defines.append(DefFact(name=name, kind=kind, docstring=_python_docstring(node, source_bytes)))

    return imports, defines
