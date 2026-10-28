import dataclasses
import json
import subprocess
from pathlib import Path

import click
from c4parser.delta import diff, render_markdown
from c4parser.exceptions import C4ValidationError

_WORKSPACE = ".seeforce/workspace.json"


def _load_rev(root: Path, rev: str) -> dict:
    try:
        result = subprocess.run(
            ["git", "show", f"{rev}:./{_WORKSPACE}"],
            cwd=root, capture_output=True, text=True, check=False,
        )
    except OSError as exc:
        raise click.ClickException(f"cannot run git: {exc}")
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        raise click.ClickException(detail[0] if detail else f"cannot read {_WORKSPACE} at {rev}")
    return _parse(result.stdout, f"{rev}:{_WORKSPACE}")


def _load_worktree(root: Path) -> dict:
    path = root / _WORKSPACE
    if not path.exists():
        raise click.ClickException(f"{_WORKSPACE} not found in {root} — run `seeforce scan .` first")
    return _parse(path.read_text(encoding="utf-8"), str(path))


def _parse(raw: str, where: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"{where} is not valid JSON: {exc}")


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
        raise click.ClickException(str(exc))

    if as_json:
        click.echo(json.dumps(dataclasses.asdict(result), indent=2))
    else:
        click.echo(render_markdown(result))
