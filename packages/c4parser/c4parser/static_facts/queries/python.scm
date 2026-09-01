(import_statement name: (dotted_name) @import)
(import_statement name: (aliased_import name: (dotted_name) @import))
(import_from_statement module_name: (dotted_name) @import)
; `from . import x` / `from .types import y` / `from ..sibling import z` parse to a
; relative_import node, not a dotted_name — without this they are never captured.
(import_from_statement module_name: (relative_import) @import)

(function_definition) @def
(class_definition) @def
