import json
from pathlib import Path
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
