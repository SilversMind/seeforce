"""
@c2:container
name: Annotation Parser
system: SeeForce
technology: Python
description: Standalone library (published as seeforce-c4parser) that parses @c1/@c2/@c3/@lexicon annotations from a repo's source files and assembles the resulting workspace.json. Independently packaged and shared by the Backend and the SeeForce CLI, not owned by either.
"""
from .scanner import scan
from .builder import build, find_orphans
from .exporter import export_workspace
from .types import C4System, C4Container, C4Component, C4Element
from .exceptions import C4ParseError, C4ValidationError

__all__ = [
    "scan",
    "build",
    "find_orphans",
    "export_workspace",
    "C4System",
    "C4Container",
    "C4Component",
    "C4Element",
    "C4ParseError",
    "C4ValidationError",
]
