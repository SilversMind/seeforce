"""
@c2:container
name: Annotation Parser
system: SeeForce
technology: Python
description: |
  - Parses @c1/@c2/@c3/@lexicon annotations from a repo's source files
  - Assembles them into workspace.json
  - Compares workspace snapshots and checks the feature catalogue
  - Extracts static import facts and entry points from source files
  - Ships as the standalone seeforce-c4parser package
short_desc: Parses C4 annotations from source files into workspace.json
"""
from .builder import (
    build,
    edge_label,
    find_empty_containers,
    find_long_short_descriptions,
    find_orphans,
    find_unreadable_descriptions,
    merge_flows,
    merge_labels,
    split_flows,
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
from .scanner import DEFAULT_EXTENSIONS, format_description, scan
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
    "edge_label",
    "element_index",
    "export_workspace",
    "find_empty_containers",
    "find_long_short_descriptions",
    "find_orphans",
    "find_unreadable_descriptions",
    "flatten",
    "format_description",
    "load_catalogue",
    "merge_flows",
    "merge_labels",
    "render_broken_features",
    "render_markdown",
    "review_flags",
    "scan",
    "split_flows",
]
