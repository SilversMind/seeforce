"""
@c3:component
name: MCP Install Command
container: SeeForce CLI
description: Registers the SeeForce MCP server in ~/.claude.json and writes the drift-sync tooling (arch-sync-check.sh Stop hook, seeforce-arch-check skill, CLAUDE.md rule section) into the target repo — the delivery mechanism that makes ongoing drift checking happen in a user's own project, not just a one-time annotate_codebase pass.
short_desc: Registers the MCP server and installs the drift-sync hook/skill
uses:
    - Backend: "Fetches the project id and validates the auth token via `seeforce mcp install`"
      technology: REST
"""
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


_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_HOOK_COMMAND = "bash .claude/hooks/arch-sync-check.sh"
_CLAUDE_MD_MARKER = "<!-- seeforce:arch-sync-section -->"


def _install_arch_sync(proj: Path) -> None:
    """Write the architecture-sync-check hook, skill, and CLAUDE.md rule into
    the target repo, so ongoing code generation there keeps C4 annotations in
    sync — not just the one-time annotate_codebase pass."""
    # Hook script — managed file, always overwritten to match the shipped version.
    hooks_dir = proj / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_dest = hooks_dir / "arch-sync-check.sh"
    hook_dest.write_text((_TEMPLATES_DIR / "arch-sync-check.sh").read_text())
    hook_dest.chmod(0o755)
    click.echo(f"Written {hook_dest.relative_to(proj)}")

    # Skill file — managed file, always overwritten.
    skills_dir = proj / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    skill_dest = skills_dir / "seeforce-arch-check.md"
    skill_dest.write_text((_TEMPLATES_DIR / "seeforce-arch-check.md").read_text())
    click.echo(f"Written {skill_dest.relative_to(proj)}")

    # settings.json — merge the Stop hook entry, never overwrite existing config.
    settings_path = proj / ".claude" / "settings.json"
    settings = _load_claude_json(settings_path)
    stop_hooks = settings.setdefault("hooks", {}).setdefault("Stop", [])
    already_wired = any(
        h.get("command") == _HOOK_COMMAND
        for entry in stop_hooks
        for h in entry.get("hooks", [])
    )
    if not already_wired:
        stop_hooks.append({"hooks": [{"type": "command", "command": _HOOK_COMMAND, "timeout": 15}]})
        _save_claude_json(settings_path, settings)
        click.echo(f"Wired Stop hook in {settings_path.relative_to(proj)}")
    else:
        click.echo(f"Stop hook already wired in {settings_path.relative_to(proj)}")

    # CLAUDE.md — append our section once; never touch existing content.
    claude_md_path = proj / "CLAUDE.md"
    snippet = (_TEMPLATES_DIR / "claude-md-snippet.md").read_text()
    if claude_md_path.exists():
        existing = claude_md_path.read_text()
        if _CLAUDE_MD_MARKER in existing:
            click.echo(f"{claude_md_path.relative_to(proj)} already has the architecture-sync section")
        else:
            claude_md_path.write_text(existing.rstrip("\n") + "\n\n" + snippet)
            click.echo(f"Appended architecture-sync section to {claude_md_path.relative_to(proj)}")
    else:
        claude_md_path.write_text(snippet)
        click.echo(f"Created {claude_md_path.relative_to(proj)}")


@click.group()
def mcp():
    """Manage SeeForce MCP server integration."""


@mcp.command("install")
@click.option("--project-path", default=".", type=click.Path(exists=True, file_okay=False),
              help="Project repo path — .c4project and the architecture-sync setup are written here.")
@click.option("--skip-project-id", is_flag=True, hidden=True,
              help="Skip .c4project fetch (for tests).")
@click.option("--skip-claude-setup", is_flag=True,
              help="Don't write the architecture-sync hook/skill/CLAUDE.md rule into the project.")
def install(project_path: str, skip_project_id: bool, skip_claude_setup: bool):
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

    proj = Path(project_path).resolve()

    if not skip_claude_setup:
        _install_arch_sync(proj)

    if not skip_project_id:
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
                latest = max(projects, key=lambda p: p.get("updated_at", ""))
                uuid = latest.get("project_id") or str(latest["id"])
                c4file.write_text(uuid)
                click.echo(f"Written .c4project ({uuid}) to {proj}")
            else:
                click.echo("No projects on server yet — import a repo in SeeForce first, then re-run this command.")

    click.echo("\nRestart Claude Code (or start a new session) to activate the MCP server.")
