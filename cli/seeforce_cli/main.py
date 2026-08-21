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
