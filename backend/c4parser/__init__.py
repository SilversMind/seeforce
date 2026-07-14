"""
@c2:container
name: c4parser
system: C4 Tool
technology: Python
description: Scans source files for C4 annotations and generates workspace.json
"""

from .scanner import scan
from .builder import build
from .exporter import export_workspace
from .types import C4System, C4Container, C4Component
from .exceptions import C4ParseError, C4ValidationError

__all__ = [
    "scan",
    "build",
    "export_workspace",
    "C4System",
    "C4Container",
    "C4Component",
    "C4ParseError",
    "C4ValidationError",
]
