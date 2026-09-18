"""
@c2:container
name: SeeForce CLI
system: SeeForce
technology: Python / Click
description: Local command-line entry point — logs in, scans a repo for @c1/@c2/@c3/@lexicon annotations, launches an LLM-guided annotation pass, and installs the SeeForce MCP server plus the drift-sync tooling (Stop hook, skill, CLAUDE.md rule) that keeps a project's annotations from drifting from its code going forward.
short_desc: CLI — login, scan, annotate, and installs the drift-sync tooling
uses:
    - Annotation Parser: "parses and builds workspace.json when scanning a repo locally via `seeforce scan`"
    - Backend: "authenticates the user, fetches the project id, and registers the MCP server against it via `seeforce mcp install`"
      technology: REST
"""
import click
from seeforce_cli.commands.login import login
from seeforce_cli.commands.scan import scan
from seeforce_cli.commands.mcp import mcp
from seeforce_cli.commands.annotate import annotate


@click.group()
@click.version_option(package_name="seeforce")
def cli():
    """SeeForce — validate C4 architecture annotations locally."""


cli.add_command(login)
cli.add_command(scan)
cli.add_command(mcp)
cli.add_command(annotate)
