import os
from pathlib import Path

API_URL = os.environ.get("SEEFORCE_API_URL", "https://seeforce.onrender.com").rstrip("/")
_TOKEN = os.environ.get("SEEFORCE_API_TOKEN", "")


def http_headers() -> dict:
    if _TOKEN:
        return {"Authorization": f"Token {_TOKEN}"}
    return {}


def resolve_project_id() -> str | None:
    explicit = os.environ.get("SEEFORCE_PROJECT_ID", "").strip()
    if explicit:
        return explicit
    cwd = Path.cwd()
    for d in [cwd, *cwd.parents]:
        p = d / ".c4project"
        if p.exists():
            val = p.read_text().strip()
            if val:
                return val
    return None
