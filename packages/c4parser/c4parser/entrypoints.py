"""
@c3:component
name: Entry Point Discovery
container: Annotation Parser
technology: Python / tree-sitter
description: |
  - Lists every deterministic way into a repo:
    - HTTP routes and REST collections
    - CLI commands
    - MCP tools
    - Page routes
  - Counts one router registration as one entry point
  - Sorts the output so two runs agree byte for byte
short_desc: Extracts a repo's routes, commands and tools as sorted entry points
"""
