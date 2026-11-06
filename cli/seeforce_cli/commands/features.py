"""
@c3:component
name: Features Command
container: SeeForce CLI
description: The `seeforce features` command — loads the catalogue and the model from the working tree, applies every fatal validation rule, and lists what the repo lets you do with capabilities and prerequisites in separate blocks. Exits 2 on a validation failure or a missing model, and 0 with an explanatory line when the repo has no catalogue yet. Reads only; it never writes or repairs the catalogue.
short_desc: Validates the feature catalogue and lists what the repo lets you do
uses:
- Feature Catalogue: "loads and validates the catalogue against the scanned workspace"
"""
import dataclasses
import json
from pathlib import Path

import click
from c4parser.exceptions import C4ValidationError
from c4parser.features import load_catalogue, review_flags

CATALOGUE = ".seeforce/features.json"
WORKSPACE = ".seeforce/workspace.json"


class LoadError(click.ClickException):
    """A usage or load failure, which contracts/cli.md gives its own exit code."""
    exit_code = 2


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LoadError(f"{path} is not valid JSON: {exc}")
    except OSError as exc:
        raise LoadError(f"cannot read {path}: {exc}")


def load_model(root: Path) -> dict:
    path = root / WORKSPACE
    if not path.exists():
        raise LoadError(
            f"{WORKSPACE} not found in {root} — the catalogue is a reading of the model, "
            "so run `seeforce scan .` first"
        )
    return read_json(path)


def _render(catalogue, flags: list[str]) -> str:
    lines: list[str] = []
    for category in catalogue.categories:
        lines += [f"## {category.name}", ""]
        for kind, heading in (("capability", "Capabilities"), ("prerequisite", "Prerequisites")):
            features = [f for f in category.features if f.kind == kind]
            if not features:
                continue
            lines += [f"### {heading}", ""]
            for feature in features:
                mark = "reviewed" if feature.reviewed else "generated"
                lines.append(f"- {feature.name} [{mark}] — {feature.intent}")
            lines.append("")
    if flags:
        lines += ["## Review flags", ""] + [f"- {flag}" for flag in flags] + [""]
    return "\n".join(lines).rstrip() or "The catalogue has no features."


@click.command()
@click.option("--path", default=".", type=click.Path(exists=True, file_okay=False),
              help="Repository root (default: current directory).")
@click.option("--json", "as_json", is_flag=True, help="Print the parsed catalogue instead of the listing.")
def features(path: str, as_json: bool):
    """Validate the catalogue against the model and list what the repo lets you do."""
    root = Path(path).resolve()
    model = load_model(root)

    catalogue_path = root / CATALOGUE
    if not catalogue_path.exists():
        click.echo(
            f"No catalogue at {CATALOGUE}. Ask your coding agent to build one — it calls the "
            "`catalogue_features` MCP tool for the guide."
        )
        return

    try:
        catalogue = load_catalogue(read_json(catalogue_path), model)
    except C4ValidationError as exc:
        raise LoadError(str(exc))

    if as_json:
        click.echo(json.dumps(dataclasses.asdict(catalogue), indent=2, ensure_ascii=False))
        return

    # Entry-point discovery is a later slice, so nothing is known to exist yet and every
    # NOTE: claimed id would read as vanished — pass the claims back as known until it lands.
    claimed = sorted({e for f in catalogue.features() for e in f.entry_points})
    click.echo(_render(catalogue, review_flags(catalogue, entry_points=claimed)))
