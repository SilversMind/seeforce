"""
@c2:container
name: SeeForce CLI
system: SeeForce
technology: Python / Click
description: |
  - Logs in to SeeForce
  - Scans a repo's annotations into workspace.json
  - Compares workspaces across revisions and checks the feature catalogue
  - Starts an annotation pass in the user's AI assistant
  - Installs the MCP server and the drift-sync tooling (Stop hook, skill, CLAUDE.md rule)
short_desc: Logs in, scans repos and installs the drift-sync tooling
uses:
    - Annotation Parser:
      - "builds workspace.json on `seeforce scan`"
      - "compares snapshots on `seeforce delta`"
      short_desc: "builds and compares workspaces"
    - Backend:
      - "authenticates the user"
      - "fetches the project id the MCP server registers against"
      short_desc: "authenticates, fetches project id"
      technology: REST
"""
import click

from seeforce_cli.commands.annotate import annotate
from seeforce_cli.commands.delta import delta
from seeforce_cli.commands.features import features
from seeforce_cli.commands.login import login
from seeforce_cli.commands.mcp import mcp
from seeforce_cli.commands.scan import scan


@click.group()
@click.version_option(package_name="seeforce")
def cli():
    """SeeForce — validate C4 architecture annotations locally."""


cli.add_command(login)
cli.add_command(scan)
cli.add_command(mcp)
cli.add_command(annotate)
cli.add_command(delta)
cli.add_command(features)
