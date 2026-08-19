import json
import os
import tempfile
from pathlib import Path

import click
import httpx

from seeforce_cli.config import load_config


def _claude_json_path() -> Path:
    return Path.home() / ".claude.json"


def _load_claude_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"{path} contains invalid JSON: {exc}") from exc


def _save_claude_json(path: Path, data: dict) -> None:
    dir_ = path.parent
    dir_.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dir_, prefix=".claude.json.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(json.dumps(data, indent=2))
        os.replace(tmp, path)
    except Exception:
        os.unlink(tmp)
        raise


@click.group()
def mcp():
    """Manage SeeForce MCP server integration."""


@mcp.command("install")
@click.option("--project-path", default=".", type=click.Path(exists=True, file_okay=False),
              help="Project repo path — .c4project written here if absent.")
@click.option("--skip-project-id", is_flag=True, hidden=True,
              help="Skip .c4project fetch (for tests).")
def install(project_path: str, skip_project_id: bool):
    """Install SeeForce MCP server into ~/.claude.json."""
    cfg = load_config()
    if not cfg["token"]:
        raise click.ClickException("Not logged in. Run: seeforce login")

    api_url = cfg["api_url"]
    token = cfg["token"]

    claude_path = _claude_json_path()
    data = _load_claude_json(claude_path)
    data.setdefault("mcpServers", {})

    data["mcpServers"]["seeforce"] = {
        "type": "stdio",
        "command": "seeforce-mcp",
        "args": [],
        "env": {
            "SEEFORCE_API_URL": api_url,
            "SEEFORCE_API_TOKEN": token,
        },
    }
    _save_claude_json(claude_path, data)
    click.echo(f"Written MCP entry 'seeforce' to {claude_path}")

    if not skip_project_id:
        proj = Path(project_path).resolve()
        c4file = proj / ".c4project"
        if c4file.exists():
            click.echo(f".c4project already exists: {c4file.read_text().strip()}")
        else:
            try:
                r = httpx.get(f"{api_url}/api/graph/", headers={"Authorization": f"Token {token}"}, timeout=10)
                r.raise_for_status()
                projects = r.json()
            except Exception as exc:
                click.echo(f"Warning: could not fetch projects ({exc}). Run 'seeforce mcp install' again after syncing.")
                projects = []

            if projects:
                latest = sorted(projects, key=lambda p: p.get("updated_at", ""), reverse=True)[0]
                uuid = latest.get("project_id") or str(latest["id"])
                c4file.write_text(uuid)
                click.echo(f"Written .c4project ({uuid}) to {proj}")
            else:
                click.echo("No projects on server yet — import a repo in SeeForce first, then re-run this command.")

    click.echo("\nRestart Claude Code (or start a new session) to activate the MCP server.")
