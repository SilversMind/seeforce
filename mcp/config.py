import os
from pathlib import Path

API_URL: str = os.environ.get("SEEFORCE_API_URL", "http://localhost:8000").rstrip("/")
API_TOKEN: str = os.environ.get("SEEFORCE_API_TOKEN", "")
_PROJECT_ID_ENV: str = os.environ.get("SEEFORCE_PROJECT_ID", "")


def resolve_project_id() -> str:
    if _PROJECT_ID_ENV:
        return _PROJECT_ID_ENV
    path = Path.cwd()
    for _ in range(8):
        candidate = path / ".c4project"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
        if path.parent == path:
            break
        path = path.parent
    return ""


def http_headers() -> dict:
    if API_TOKEN:
        return {"Authorization": f"Token {API_TOKEN}"}
    return {}
