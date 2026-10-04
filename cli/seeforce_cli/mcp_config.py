import os
from pathlib import Path

API_URL = os.environ.get("SEEFORCE_API_URL", "https://seeforce.io").rstrip("/")
_TOKEN = os.environ.get("SEEFORCE_API_TOKEN", "")

# A worktree's .git is a file, not a directory, so test for existence, not is_dir().
_ROOT_MARKERS = (".c4project", ".seeforce", ".git")


def http_headers() -> dict:
    if _TOKEN:
        return {"Authorization": f"Token {_TOKEN}"}
    return {}


def _walk_up_for_marker(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if any((d / marker).exists() for marker in _ROOT_MARKERS):
            return d
    return None


def resolve_project_root(file_paths: list[str] | None = None) -> Path:
    """Locate the repo the agent is actually working in, for this one call.

    The MCP server is launched once, inherits one working directory, and keeps
    it for its whole life — but the agent may switch to a git worktree or to
    another repo entirely at any point during that life, and nothing notifies
    the server. Trusting the launch directory therefore means silently reading
    a different tree than the one being edited: the wrong files for static
    facts, and, once the .c4project found by walking up differs, the wrong
    project's architecture.

    The file paths the agent passes are the only live signal of where it is, so
    derive the root from those and fall back to the launch directory.
    """
    for raw in file_paths or []:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        if not candidate.exists():
            continue
        start = candidate if candidate.is_dir() else candidate.parent
        if root := _walk_up_for_marker(start):
            return root
    # ponytail: no paths means no signal — get_context and find_component still
    # resolve against the launch directory. MCP roots (session.list_roots) would
    # cover that case if Claude Code advertises them.
    return _walk_up_for_marker(Path.cwd()) or Path.cwd()


def resolve_project_id(root: Path | None = None) -> str | None:
    explicit = os.environ.get("SEEFORCE_PROJECT_ID", "").strip()
    if explicit:
        return explicit
    start = root or Path.cwd()
    for d in [start, *start.parents]:
        p = d / ".c4project"
        if p.exists():
            val = p.read_text().strip()
            if val:
                return val
    return None
