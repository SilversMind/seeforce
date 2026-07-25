"""
@c3:component
name: Architecture Scanner
container: Backend
description: Scans source files for C4 annotations and generates workspace.json
"""

from .builder import build
from .exceptions import C4ParseError, C4ValidationError
from .exporter import export_workspace
from .scanner import scan
from .types import C4Component, C4Container, C4System

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
