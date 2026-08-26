"""
@c2:container
name: Annotation Parser
system: SeeForce
technology: Python
description: Standalone library (published as seeforce-c4parser) that parses @c1/@c2/@c3/@lexicon annotations from a repo's source files and assembles the resulting workspace.json. Independently packaged and shared by the Backend and the SeeForce CLI, not owned by either.
"""
from .builder import build, find_orphans
from .exceptions import C4ParseError, C4ValidationError
from .exporter import export_workspace
from .scanner import scan
from .types import C4Component, C4Container, C4System

__all__ = [
    "scan",
    "build",
    "find_orphans",
    "export_workspace",
    "C4System",
    "C4Container",
    "C4Component",
    "C4ParseError",
    "C4ValidationError",
]
