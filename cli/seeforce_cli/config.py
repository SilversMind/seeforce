import tomllib
from pathlib import Path


def config_path() -> Path:
    return Path.home() / ".config" / "seeforce" / "config.toml"


def load_config() -> dict:
    path = config_path()
    defaults = {"api_url": "https://seeforce.onrender.com", "token": None}
    if not path.exists():
        return defaults
    with path.open("rb") as f:
        data = tomllib.load(f)
    api = data.get("api", {})
    return {
        "api_url": api.get("url", defaults["api_url"]).rstrip("/"),
        "token": api.get("token") or None,
    }


def save_config(api_url: str, token: str) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f'[api]\nurl = "{api_url.rstrip("/")}"\ntoken = "{token}"\n'
    path.write_text(content, encoding="utf-8")
