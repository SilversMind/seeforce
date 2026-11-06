"""
@c3:component
name: Entry Point Discovery
container: Annotation Parser
technology: Python / tree-sitter
description: Finds every deterministic way into a repo — HTTP routes, REST collection registrations, CLI commands, MCP tools and page routes — by querying call sites and decorators in the syntax tree rather than module-level list literals, which a URL conf assembled inside a function would hide entirely. Counts one router registration as one entry point rather than one per generated method route, and excludes catch-all fallback routes. Output is sorted so two runs over one tree agree byte for byte. Feeds new-feature detection, which keys on entry points because regenerating the catalogue is not reproducible.
short_desc: Extracts a repo's routes, commands and tools as sorted entry points
"""
