import json
from unittest.mock import patch

from click.testing import CliRunner
from seeforce_cli.main import cli


def _config(tmp_path, api_url="https://example.com", token="tok123"):
    return {"api_url": api_url, "token": token}


def test_mcp_install_writes_claude_json(tmp_path):
    claude_json = tmp_path / ".claude.json"
    with patch("seeforce_cli.commands.mcp.load_config", return_value=_config(tmp_path)), \
         patch("seeforce_cli.commands.mcp._claude_json_path", return_value=claude_json):
        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "install", "--project-path", str(tmp_path), "--skip-project-id"])
    assert result.exit_code == 0, result.output
    data = json.loads(claude_json.read_text())
    assert "seeforce" in data["mcpServers"]
    entry = data["mcpServers"]["seeforce"]
    assert entry["type"] == "stdio"
    assert entry["env"]["SEEFORCE_API_TOKEN"] == "tok123"


def test_mcp_install_fails_without_token(tmp_path):
    claude_json = tmp_path / ".claude.json"
    with patch("seeforce_cli.commands.mcp.load_config", return_value={"api_url": "https://x.com", "token": None}), \
         patch("seeforce_cli.commands.mcp._claude_json_path", return_value=claude_json):
        runner = CliRunner()
        result = runner.invoke(cli, ["mcp", "install", "--project-path", str(tmp_path)])
    assert result.exit_code != 0
    assert "login" in result.output.lower()


def test_mcp_install_preserves_existing_mcp_entries(tmp_path):
    claude_json = tmp_path / ".claude.json"
    claude_json.write_text(json.dumps({"mcpServers": {"other-tool": {"type": "stdio"}}}))
    with patch("seeforce_cli.commands.mcp.load_config", return_value=_config(tmp_path)), \
         patch("seeforce_cli.commands.mcp._claude_json_path", return_value=claude_json):
        runner = CliRunner()
        runner.invoke(cli, ["mcp", "install", "--project-path", str(tmp_path), "--skip-project-id"])
    data = json.loads(claude_json.read_text())
    assert "other-tool" in data["mcpServers"]
    assert "seeforce" in data["mcpServers"]


def _run_install(tmp_path, extra_args=None):
    claude_json = tmp_path / ".claude.json"
    with patch("seeforce_cli.commands.mcp.load_config", return_value=_config(tmp_path)), \
         patch("seeforce_cli.commands.mcp._claude_json_path", return_value=claude_json):
        runner = CliRunner()
        args = ["mcp", "install", "--project-path", str(tmp_path), "--skip-project-id"]
        result = runner.invoke(cli, args + (extra_args or []))
    assert result.exit_code == 0, result.output
    return result


def test_mcp_install_writes_arch_sync_files(tmp_path):
    _run_install(tmp_path)
    hook = tmp_path / ".claude" / "hooks" / "arch-sync-check.sh"
    skill = tmp_path / ".claude" / "skills" / "seeforce-arch-check.md"
    settings = tmp_path / ".claude" / "settings.json"
    claude_md = tmp_path / "CLAUDE.md"
    assert hook.exists() and hook.stat().st_mode & 0o111  # executable
    assert skill.exists()
    assert "seeforce-arch-check" in skill.read_text()
    data = json.loads(settings.read_text())
    assert data["hooks"]["Stop"][0]["hooks"][0]["command"] == "bash .claude/hooks/arch-sync-check.sh"
    assert "<!-- seeforce:arch-sync-section -->" in claude_md.read_text()


def test_mcp_install_appends_to_existing_claude_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("# My project rules\nDo the thing.\n")
    _run_install(tmp_path)
    content = (tmp_path / "CLAUDE.md").read_text()
    assert "My project rules" in content
    assert "Do the thing." in content
    assert "<!-- seeforce:arch-sync-section -->" in content


def test_mcp_install_preserves_existing_settings_hooks(tmp_path):
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir()
    (settings_dir / "settings.json").write_text(json.dumps({
        "hooks": {"PostToolUse": [{"matcher": "Write|Edit", "hooks": [{"type": "command", "command": "prettier --write"}]}]},
        "permissions": {"allow": ["Bash(npm *)"]},
    }))
    _run_install(tmp_path)
    data = json.loads((settings_dir / "settings.json").read_text())
    assert data["hooks"]["PostToolUse"][0]["hooks"][0]["command"] == "prettier --write"
    assert data["permissions"]["allow"] == ["Bash(npm *)"]
    assert data["hooks"]["Stop"][0]["hooks"][0]["command"] == "bash .claude/hooks/arch-sync-check.sh"


def test_mcp_install_is_idempotent(tmp_path):
    _run_install(tmp_path)
    claude_md_first = (tmp_path / "CLAUDE.md").read_text()
    settings_first = (tmp_path / ".claude" / "settings.json").read_text()
    _run_install(tmp_path)
    claude_md_second = (tmp_path / "CLAUDE.md").read_text()
    settings_second = (tmp_path / ".claude" / "settings.json").read_text()
    assert claude_md_first == claude_md_second
    assert settings_first == settings_second
    assert claude_md_second.count("<!-- seeforce:arch-sync-section -->") == 1
    assert json.loads(settings_second)["hooks"]["Stop"].__len__() == 1


def test_mcp_install_skip_claude_setup(tmp_path):
    _run_install(tmp_path, extra_args=["--skip-claude-setup"])
    assert not (tmp_path / ".claude" / "hooks" / "arch-sync-check.sh").exists()
    assert not (tmp_path / ".claude" / "skills" / "seeforce-arch-check.md").exists()
    assert not (tmp_path / "CLAUDE.md").exists()
