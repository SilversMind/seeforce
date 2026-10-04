import json
import textwrap
from pathlib import Path

from click.testing import CliRunner
from seeforce_cli.main import cli


def _write_annotated_repo(tmp_path: Path):
    (tmp_path / "app.py").write_text(textwrap.dedent('''
        """
        @c1:system
        name: MyApp
        description: Test system
        """
        """
        @c2:container
        name: API
        system: MyApp
        technology: Python
        """
    '''))
    return tmp_path


def test_scan_prints_summary(tmp_path):
    _write_annotated_repo(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "MyApp" in result.output
    assert "2" in result.output  # 2 elements found


def test_scan_writes_workspace_json(tmp_path):
    """The backend, the GitHub import and the README all read .seeforce/workspace.json."""
    _write_annotated_repo(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["scan", str(tmp_path)])
    ws_file = tmp_path / ".seeforce" / "workspace.json"
    assert ws_file.exists()
    assert not (tmp_path / "workspace.json").exists()
    data = json.loads(ws_file.read_text())
    assert data["name"] == "MyApp"


def test_scan_no_annotations_exits_cleanly(tmp_path):
    (tmp_path / "empty.py").write_text("x = 1")
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "No C4 annotations" in result.output


def test_scan_reports_validation_error(tmp_path):
    (tmp_path / "bad.py").write_text(textwrap.dedent('''
        """
        @c1:system
        name: MyApp
        """
        """
        @c3:component
        name: Orphan
        container: NonExistent
        """
    '''))
    runner = CliRunner()
    result = runner.invoke(cli, ["scan", str(tmp_path)])
    assert result.exit_code != 0 or "error" in result.output.lower()


def test_scan_dry_run_does_not_write_file(tmp_path):
    _write_annotated_repo(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["scan", "--dry-run", str(tmp_path)])
    assert not (tmp_path / ".seeforce" / "workspace.json").exists()
