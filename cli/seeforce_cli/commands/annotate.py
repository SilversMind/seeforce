"""
@c3:component
name: Annotate Command
container: SeeForce CLI
description: The `seeforce annotate` command — prints the instructions for starting an annotation pass in the user's own coding assistant, which then fetches the guide over MCP. It calls no model and writes no annotation itself; this is the boundary that keeps every other command in this CLI deterministic.
short_desc: Prints how to start an annotation pass in the user's AI assistant
uses:
- MCP Server/Tool Handlers: "names the server the assistant fetches the annotation guide from"
"""
import click


@click.command()
def annotate():
    """Annotate your codebase with C4 architecture markers using your AI assistant."""
    click.echo("Open Claude Code (or Cursor) in your project and say:")
    click.echo("")
    click.echo('  "Annotate my codebase with C4"')
    click.echo("")
    click.echo("The SeeForce MCP server will provide the annotation guide automatically.")
    click.echo("Not installed yet? Run: seeforce mcp install")
    click.echo("")
    click.echo("Once annotations are written:")
    click.echo("  seeforce scan .          # validate")
    click.echo("  git add -A && git commit  # commit")
