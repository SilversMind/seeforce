import tomllib
from pathlib import Path
import pytest
from unittest.mock import patch
from seeforce_cli.config import load_config, save_config, config_path


def _mock_config_path(tmp_path):
    return tmp_path / "config.toml"


def test_load_config_returns_defaults_when_no_file(tmp_path):
    with patch("seeforce_cli.config.config_path", return_value=tmp_path / "config.toml"):
        cfg = load_config()
    assert cfg["api_url"] == "https://seeforce.onrender.com"
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
