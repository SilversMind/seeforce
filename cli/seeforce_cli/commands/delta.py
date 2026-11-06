"""
@c3:component
name: Delta Command
container: SeeForce CLI
description: The `seeforce delta` command — reads a `.seeforce/workspace.json` at two revisions out of git, prints what changed architecturally, and then reports every catalogue feature that names an element the comparison removed. Exits 1 when a feature is broken, 2 on a revision that does not exist or a failed load, and 0 when the model changed but no feature did — a changed architecture is not a failure. Writes nothing and repairs nothing.
short_desc: Compares two revisions' workspaces and fails CI on a broken feature
uses:
- Delta Reporter: "compares the two snapshots and intersects the catalogue against the removed elements"
- Feature Catalogue: "loads and validates the working tree's catalogue against the head snapshot"
"""
import dataclasses
import json
import subprocess
from pathlib import Path

import click
from c4parser.delta import (
    broken_features,
    diff,
    render_broken_features,
    render_markdown,
)
from c4parser.exceptions import C4ValidationError
from c4parser.features import load_catalogue

from seeforce_cli.commands.features import CATALOGUE, LoadError, read_json

_WORKSPACE = ".seeforce/workspace.json"


def _load_catalogue(root: Path, base_ws: dict):
    """Return the working tree's catalogue validated against the BASE model, or None if there is none.
    NOTE: against head, a broken feature would be a fatal load error instead and exit 1 unreachable.
    """
    path = root / CATALOGUE
    if not path.exists():
        return None
    try:
        return load_catalogue(read_json(path), base_ws)
    except C4ValidationError as exc:
        raise LoadError(str(exc))


def _load_rev(root: Path, rev: str) -> dict:
    try:
        result = subprocess.run(
            ["git", "show", f"{rev}:./{_WORKSPACE}"],
            cwd=root, capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        raise LoadError(f"cannot run git: {exc}")
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        raise LoadError(detail[0] if detail else f"cannot read {_WORKSPACE} at {rev}")
    return _parse(result.stdout, f"{rev}:{_WORKSPACE}")


def _load_worktree(root: Path) -> dict:
    path = root / _WORKSPACE
    if not path.exists():
        raise LoadError(f"{_WORKSPACE} not found in {root} — run `seeforce scan .` first")
    return _parse(path.read_text(encoding="utf-8"), str(path))


def _parse(raw: str, where: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LoadError(f"{where} is not valid JSON: {exc}")


@click.command()
@click.argument("base_rev")
@click.argument("head_rev", required=False)
@click.option("--path", default=".", type=click.Path(exists=True, file_okay=False),
              help="Repository root (default: current directory).")
@click.option("--json", "as_json", is_flag=True, help="Print the delta structure instead of markdown.")
def delta(base_rev: str, head_rev: str | None, path: str, as_json: bool):
    """Report what changed architecturally between BASE_REV and HEAD_REV.

    HEAD_REV defaults to the working tree.
    """
    root = Path(path).resolve()
    base_ws = _load_rev(root, base_rev)
    head_ws = _load_rev(root, head_rev) if head_rev else _load_worktree(root)

    try:
        result = diff(base_ws, head_ws)
    except C4ValidationError as exc:
        raise LoadError(str(exc))

    catalogue = _load_catalogue(root, base_ws)
    broken = broken_features(catalogue, result) if catalogue else {}

    if as_json:
        payload = dataclasses.asdict(result)
        payload["broken_features"] = broken
        click.echo(json.dumps(payload, indent=2))
    else:
        click.echo(render_markdown(result))
        if catalogue:
            click.echo("")
            click.echo(render_broken_features(broken))

    if broken:
        raise SystemExit(1)
