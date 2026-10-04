import os
import tomllib
from pathlib import Path


def config_path() -> Path:
    return Path.home() / ".config" / "seeforce" / "config.toml"


def load_config() -> dict:
    path = config_path()
    defaults = {"api_url": "https://seeforce.io", "token": None}
    if not path.exists():
        return defaults
    with path.open("rb") as f:
        data = tomllib.load(f)
    api = data.get("api", {})
    return {
        "api_url": api.get("url", defaults["api_url"]).rstrip("/"),
        "token": api.get("token") or None,
    }


def _toml_str(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def save_config(api_url: str, token: str) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f'[api]\nurl = "{_toml_str(api_url.rstrip("/"))}"\ntoken = "{_toml_str(token)}"\n'
    path.write_text(content, encoding="utf-8")
    os.chmod(path, 0o600)
