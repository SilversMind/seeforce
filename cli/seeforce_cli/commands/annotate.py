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
