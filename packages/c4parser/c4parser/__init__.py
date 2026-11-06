"""
@c2:container
name: Annotation Parser
system: SeeForce
technology: Python
description: Standalone library (published as seeforce-c4parser) that parses @c1/@c2/@c3/@lexicon annotations from a repo's source files and assembles the resulting workspace.json. Independently packaged and shared by the Backend and the SeeForce CLI, not owned by either.
short_desc: Parses C4 annotations from source files into workspace.json
"""
from .builder import (
    build,
    find_empty_containers,
    find_long_short_descriptions,
    find_orphans,
)
from .delta import (
    Delta,
    broken_features,
    diff,
    flatten,
    render_broken_features,
    render_markdown,
)
from .exceptions import C4ParseError, C4ValidationError
from .exporter import export_workspace
from .features import (
    Catalogue,
    Category,
    Feature,
    dump_catalogue,
    element_index,
    load_catalogue,
    review_flags,
)
from .scanner import DEFAULT_EXTENSIONS, scan
from .types import C4Component, C4Container, C4Element, C4System

__all__ = [
    "DEFAULT_EXTENSIONS",
    "C4Component",
    "C4Container",
    "C4Element",
    "C4ParseError",
    "C4System",
    "C4ValidationError",
    "Catalogue",
    "Category",
    "Delta",
    "Feature",
    "broken_features",
    "build",
    "diff",
    "dump_catalogue",
    "element_index",
    "export_workspace",
    "find_empty_containers",
    "find_long_short_descriptions",
    "find_orphans",
    "flatten",
    "load_catalogue",
    "render_broken_features",
    "render_markdown",
    "review_flags",
    "scan",
]
