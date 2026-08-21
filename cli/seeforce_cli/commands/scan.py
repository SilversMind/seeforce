import json
import sys
from pathlib import Path
from typing import Optional

import click
import c4parser
from c4parser.exceptions import C4ParseError, C4ValidationError


@click.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--dry-run", is_flag=True, help="Print workspace JSON without writing file.")
@click.option("--output", "-o", default=None, help="Output file path (default: <path>/workspace.json).")
def scan(path: str, dry_run: bool, output: Optional[str]):
    """Scan PATH for C4 annotations and validate the workspace."""
    root = Path(path).resolve()

    click.echo(f"Scanning {root}...")
    try:
        elements = c4parser.scan(str(root))
    except C4ParseError as exc:
        raise click.ClickException(str(exc))

    if not elements:
        click.echo("No C4 annotations found.")
        return

    try:
        workspace = c4parser.build(elements)
    except C4ValidationError as exc:
        click.echo(f"Validation error: {exc}", err=True)
        sys.exit(1)

    systems = workspace["model"]["softwareSystems"]
    n_containers = sum(len(s.get("containers", [])) for s in systems)
    n_components = sum(
        len(c.get("components", []))
        for s in systems
        for c in s.get("containers", [])
    )
    n_lexicon = len(workspace.get("lexicon", []))
    lexicon_note = f", {n_lexicon} lexicon entr{'y' if n_lexicon == 1 else 'ies'}" if n_lexicon else ""
    click.echo(
        f"Found {len(elements)} elements — "
        f"{len(systems)} system(s), {n_containers} container(s), {n_components} component(s){lexicon_note}"
    )
    click.echo(f"Workspace: {workspace['name']}")

    if dry_run:
        click.echo(json.dumps(workspace, indent=2))
        return

    out_path = Path(output) if output else root / "workspace.json"
    out_path.write_text(c4parser.export_workspace(workspace), encoding="utf-8")
    click.echo(f"Written: {out_path}")
