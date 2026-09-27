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
from .exceptions import C4ParseError, C4ValidationError
from .exporter import export_workspace
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
    "build",
    "export_workspace",
    "find_empty_containers",
    "find_long_short_descriptions",
    "find_orphans",
    "scan",
]
