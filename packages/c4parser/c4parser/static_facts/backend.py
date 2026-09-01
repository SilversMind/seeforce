from pathlib import Path

import tree_sitter
from tree_sitter_language_pack import get_language, get_parser

from .types import DefFact

_QUERIES_DIR = Path(__file__).parent / "queries"
_PYTHON_QUERY = (_QUERIES_DIR / "python.scm").read_text()
_TYPESCRIPT_QUERY = (_QUERIES_DIR / "typescript.scm").read_text()


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


# `export function f() {}` / `export default class C {}` nest the declaration inside
# a wrapper node, so the preceding comment is the *wrapper's* previous sibling, not
# the declaration's. Without walking up, every exported symbol loses its docstring.
_TS_DECL_WRAPPERS = {"export_statement", "ambient_declaration"}


def _clean_jsdoc(text: str) -> str:
    """Flatten a /** ... */ block to a single line: drop the delimiters and each
    line's leading `*` gutter, then join the remaining lines with spaces. Kept to
    one line on purpose — this feeds the MCP tool's one-line-per-definition output."""
    body = text
    if body.startswith("/**"):
        body = body[3:]
    elif body.startswith("/*"):
        body = body[2:]
    if body.endswith("*/"):
        body = body[:-2]

    lines: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("*"):
            line = line[1:].strip()
        if line:
            lines.append(line)
    return " ".join(lines)


def _typescript_docstring(def_node, source_bytes: bytes) -> str:
    node = def_node
    while node.parent is not None and node.parent.type in _TS_DECL_WRAPPERS:
        node = node.parent

    prev = node.prev_sibling
    if prev is not None and prev.type == "comment":
        text = _node_text(prev, source_bytes)
        if text.startswith("/**"):
            return _clean_jsdoc(text)
    return ""


def extract_typescript(file_path: str, source: str) -> tuple[list[str], list[DefFact]]:
    parser = get_parser("typescript")
    language = get_language("typescript")
    source_bytes = source.encode("utf-8")
    tree = parser.parse(source_bytes)

    query = tree_sitter.Query(language, _TYPESCRIPT_QUERY)
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node)

    imports = [_node_text(n, source_bytes).strip("'\"") for n in captures.get("import", [])]

    defines: list[DefFact] = []
    for node in captures.get("def", []):
        name_node = node.child_by_field_name("name")
        name = _node_text(name_node, source_bytes) if name_node else ""
        kind = "class" if node.type == "class_declaration" else "function"
        defines.append(DefFact(name=name, kind=kind, docstring=_typescript_docstring(node, source_bytes)))

    return imports, defines
