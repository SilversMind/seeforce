import click


@click.group()
@click.version_option(package_name="seeforce")
def cli():
    """SeeForce — validate C4 architecture annotations locally."""
