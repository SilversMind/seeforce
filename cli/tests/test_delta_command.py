import json
import subprocess
from pathlib import Path

from click.testing import CliRunner
from seeforce_cli.main import cli


def _ws(description="old"):
    return {"name": "T", "model": {"softwareSystems": [{
        "id": "sys", "name": "Sys",
        "containers": [{"id": "cont", "name": "Backend", "source_file": "b.py",
                        "description": description}],
    }]}}


def _repo(tmp_path: Path, base_ws: dict, head_ws: dict | None) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "commit.gpgsign", "false"], cwd=tmp_path, check=True)
    seeforce = tmp_path / ".seeforce"
    seeforce.mkdir()
    target = seeforce / "workspace.json"
    target.write_text(json.dumps(base_ws))
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base", "--no-verify"], cwd=tmp_path, check=True)
    if head_ws is not None:
        target.write_text(json.dumps(head_ws))
    return tmp_path


def test_delta_compares_a_revision_to_the_working_tree(tmp_path):
    root = _repo(tmp_path, _ws("old"), _ws("new"))
    result = CliRunner().invoke(cli, ["delta", "HEAD", "--path", str(root)])
    assert result.exit_code == 0, result.output
    assert "description: old → new" in result.output


def test_delta_reports_no_change(tmp_path):
    root = _repo(tmp_path, _ws("same"), None)
    result = CliRunner().invoke(cli, ["delta", "HEAD", "--path", str(root)])
    assert result.exit_code == 0
    assert "No architecture changes." in result.output


def test_delta_json_flag_emits_the_structure(tmp_path):
    root = _repo(tmp_path, _ws("old"), _ws("new"))
    result = CliRunner().invoke(cli, ["delta", "HEAD", "--path", str(root), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["changed"][0]["fields"][0]["field"] == "description"


def test_delta_explains_an_unknown_revision(tmp_path):
    root = _repo(tmp_path, _ws(), _ws("new"))
    result = CliRunner().invoke(cli, ["delta", "no-such-rev", "--path", str(root)])
    assert result.exit_code != 0
    assert "no-such-rev" in result.output


def test_delta_explains_invalid_json_in_the_working_tree(tmp_path):
    root = _repo(tmp_path, _ws(), None)
    (root / ".seeforce" / "workspace.json").write_text("{not json")
    result = CliRunner().invoke(cli, ["delta", "HEAD", "--path", str(root)])
    assert result.exit_code != 0
    assert "not valid JSON" in result.output


def test_delta_explains_a_missing_working_tree_file(tmp_path):
    root = _repo(tmp_path, _ws(), None)
    (root / ".seeforce" / "workspace.json").unlink()
    result = CliRunner().invoke(cli, ["delta", "HEAD", "--path", str(root)])
    assert result.exit_code != 0
    assert "workspace.json" in result.output


def test_delta_explains_a_missing_git(tmp_path, monkeypatch):
    def no_git(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", "git")

    monkeypatch.setattr(subprocess, "run", no_git)
    result = CliRunner().invoke(cli, ["delta", "HEAD", "--path", str(tmp_path)])
    assert result.exit_code != 0
    assert "cannot run git" in result.output
    assert "Traceback" not in result.output


def test_delta_path_reads_the_subdirectory_history_not_the_root(tmp_path):
    root = _repo(tmp_path, _ws("root"), None)
    sub = root / "sub" / ".seeforce"
    sub.mkdir(parents=True)
    (sub / "workspace.json").write_text(json.dumps(_ws("s1")))
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "sub", "--no-verify"], cwd=root, check=True)
    (sub / "workspace.json").write_text(json.dumps(_ws("s2")))
    result = CliRunner().invoke(cli, ["delta", "HEAD", "--path", str(root / "sub")])
    assert result.exit_code == 0
    assert "s1 → s2" in result.output


def test_delta_explains_a_revision_without_a_workspace_file(tmp_path):
    root = _repo(tmp_path, _ws(), None)
    subprocess.run(["git", "rm", "-q", ".seeforce/workspace.json"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "rm", "--no-verify"], cwd=root, check=True)
    result = CliRunner().invoke(cli, ["delta", "HEAD", "--path", str(root)])
    assert result.exit_code != 0
    assert "workspace.json" in result.output
    assert "Traceback" not in result.output


def test_delta_explains_a_workspace_that_is_not_an_object(tmp_path):
    root = _repo(tmp_path, [], _ws())
    result = CliRunner().invoke(cli, ["delta", "HEAD", "--path", str(root)])
    assert result.exit_code != 0
    assert "must be a JSON object" in result.output
    assert "Traceback" not in result.output
