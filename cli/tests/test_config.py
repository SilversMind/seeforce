from unittest.mock import patch

from seeforce_cli.config import load_config, save_config


def _mock_config_path(tmp_path):
    return tmp_path / "config.toml"


def test_load_config_returns_defaults_when_no_file(tmp_path):
    with patch("seeforce_cli.config.config_path", return_value=tmp_path / "config.toml"):
        cfg = load_config()
    assert cfg["api_url"] == "https://seeforce.io"
    assert cfg["token"] is None


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "config.toml"
    with patch("seeforce_cli.config.config_path", return_value=path):
        save_config("https://example.com", "tok123")
        cfg = load_config()
    assert cfg["api_url"] == "https://example.com"
    assert cfg["token"] == "tok123"


def test_save_config_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "config.toml"
    with patch("seeforce_cli.config.config_path", return_value=path):
        save_config("https://example.com", "tok123")
    assert path.exists()


def test_load_config_strips_trailing_slash(tmp_path):
    path = tmp_path / "config.toml"
    with patch("seeforce_cli.config.config_path", return_value=path):
        save_config("https://example.com/", "tok123")
        cfg = load_config()
    assert cfg["api_url"] == "https://example.com"


def test_resolve_project_root_follows_the_paths_not_the_cwd(tmp_path, monkeypatch):
    # The server is launched in `main` and never told the agent moved to
    # `worktree`; the paths it is handed are the only signal it has.
    from seeforce_cli.mcp_config import resolve_project_root

    main = tmp_path / "main"
    (main / ".git").mkdir(parents=True)
    worktree = tmp_path / "worktree"
    edited = worktree / "cli" / "thing.py"
    edited.parent.mkdir(parents=True)
    edited.write_text("x = 1\n")
    # A linked worktree marks its root with a .git FILE, not a directory.
    (worktree / ".git").write_text("gitdir: elsewhere")

    monkeypatch.chdir(main)
    assert resolve_project_root([str(edited)]) == worktree
    assert resolve_project_root() == main
    # A path that does not exist carries no signal, so fall back instead of guessing.
    assert resolve_project_root(["nope/missing.py"]) == main
