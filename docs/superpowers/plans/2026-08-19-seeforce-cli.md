# SeeForce CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `seeforce` Python CLI installable via `curl -fsSL https://seeforce.onrender.com/install.sh | sh` that lets developers validate C4 annotations locally, configure the MCP server, and authenticate with SeeForce via GitHub OAuth.

**Architecture:** Three pillars. (1) `packages/c4parser/` — shared Python package used by both backend and CLI, single source of truth for annotation parsing. (2) `cli/` — Click-based CLI that validates annotations locally and writes `workspace.json`, never pushes to the API directly (GitHub import + branch sync is the only SeeForce update mechanism). (3) Backend adds one OAuth endpoint (`/cli/auth/`) for the localhost-callback login flow.

**Tech Stack:** Python 3.11+, Click, httpx, PyYAML, hatchling (build), uv (distribution)

**Spec:** This document. GitHub import + branch sync is the existing SeeForce update path — CLI does not replace it, only augments it with local validation.

## Global Constraints

- Python ≥ 3.11 (tomllib is stdlib)
- No Django dependency in `packages/c4parser/` or `cli/`
- CLI never POSTs workspace JSON — local validation only
- Default API URL: `https://seeforce.onrender.com`
- Auth header: `Authorization: Token <key>` (DRF Token auth)
- Config file: `~/.config/seeforce/config.toml`
- Package entry points: `seeforce` → `seeforce_cli.main:cli`, `seeforce-mcp` → `seeforce_cli.mcp_server:main`
- install.sh uses uv: `uv tool install git+https://github.com/SilversMind/seeforce.git#subdirectory=cli`

---

### Task 1: Extract shared `packages/c4parser/` package

**Files:**
- Create: `packages/c4parser/pyproject.toml`
- Create: `packages/c4parser/c4parser/__init__.py`
- Create: `packages/c4parser/c4parser/types.py` (move from `backend/c4parser/types.py`)
- Create: `packages/c4parser/c4parser/exceptions.py` (move from `backend/c4parser/exceptions.py`)
- Create: `packages/c4parser/c4parser/scanner.py` (move from `backend/c4parser/scanner.py`)
- Create: `packages/c4parser/c4parser/builder.py` (move from `backend/c4parser/builder.py`)
- Create: `packages/c4parser/c4parser/exporter.py` (move from `backend/c4parser/exporter.py`)
- Modify: `backend/c4parser/__init__.py` — re-export from shared package
- Modify: `backend/c4parser/types.py` → delete content, import from shared
- Modify: `backend/c4parser/exceptions.py` → delete content, import from shared
- Modify: `backend/c4parser/scanner.py` → delete content, import from shared
- Modify: `backend/c4parser/builder.py` → delete content, import from shared
- Modify: `backend/c4parser/exporter.py` → delete content, import from shared
- Modify: `backend/pyproject.toml` — add `seeforce-c4parser` local dep

**Interfaces:**
- Consumes: existing `backend/c4parser/` files (verbatim copy, no logic changes)
- Produces: `import c4parser` works identically from both backend and CLI; all existing backend tests still pass

- [ ] **Step 1: Create packages/c4parser/pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "seeforce-c4parser"
version = "0.1.0"
description = "Shared C4 annotation parser for SeeForce"
requires-python = ">=3.11"
dependencies = ["pyyaml>=6.0"]

[tool.hatch.build.targets.wheel]
packages = ["c4parser"]
```

- [ ] **Step 2: Copy source files into packages/c4parser/c4parser/**

Copy each file verbatim — no logic changes:
- `backend/c4parser/types.py` → `packages/c4parser/c4parser/types.py`
- `backend/c4parser/exceptions.py` → `packages/c4parser/c4parser/exceptions.py`
- `backend/c4parser/scanner.py` → `packages/c4parser/c4parser/scanner.py`
- `backend/c4parser/builder.py` → `packages/c4parser/c4parser/builder.py`
- `backend/c4parser/exporter.py` → `packages/c4parser/c4parser/exporter.py`

Fix imports inside the copied files: change `from .types import` / `from .exceptions import` to remain as relative imports within the new package — they already use relative imports so no change needed.

Create `packages/c4parser/c4parser/__init__.py`:
```python
from .scanner import scan
from .builder import build
from .exporter import export_workspace
from .types import C4System, C4Container, C4Component, C4Element
from .exceptions import C4ParseError, C4ValidationError
```

- [ ] **Step 3: Update backend/c4parser/ to re-export from shared package**

Replace contents of each backend file to delegate to the shared package.

`backend/c4parser/types.py`:
```python
from c4parser.types import C4System, C4Container, C4Component, C4Element
__all__ = ["C4System", "C4Container", "C4Component", "C4Element"]
```

`backend/c4parser/exceptions.py`:
```python
from c4parser.exceptions import C4ParseError, C4ValidationError
__all__ = ["C4ParseError", "C4ValidationError"]
```

`backend/c4parser/scanner.py`:
```python
from c4parser.scanner import scan
__all__ = ["scan"]
```

`backend/c4parser/builder.py`:
```python
from c4parser.builder import build
__all__ = ["build"]
```

`backend/c4parser/exporter.py`:
```python
from c4parser.exporter import export_workspace
__all__ = ["export_workspace"]
```

`backend/c4parser/__init__.py`:
```python
from c4parser import scan, build, export_workspace, C4System, C4Container, C4Component, C4Element
from c4parser.exceptions import C4ParseError, C4ValidationError
```

- [ ] **Step 4: Add shared package to backend dependencies**

In `backend/pyproject.toml`, add to `[project.dependencies]`:
```toml
"seeforce-c4parser @ file:///${PROJECT_ROOT}/../packages/c4parser",
```

Or using uv workspace syntax in `backend/pyproject.toml`:
```toml
[tool.uv.sources]
seeforce-c4parser = { path = "../packages/c4parser", editable = true }
```

And add to dependencies list: `"seeforce-c4parser>=0.1.0"`.

- [ ] **Step 5: Reinstall backend with new dep**

```bash
cd backend && uv sync
```

Expected: resolves `seeforce-c4parser` from local path, no errors.

- [ ] **Step 6: Run existing backend c4parser tests**

```bash
cd backend && python -m pytest tests/c4parser/ -v
```

Expected: all tests pass (zero logic changes).

- [ ] **Step 7: Run full backend test suite**

```bash
cd backend && python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add packages/ backend/c4parser/ backend/pyproject.toml backend/uv.lock
git commit -m "refactor: extract c4parser into shared packages/c4parser/ package"
```

---

### Task 2: Scaffold CLI package

**Files:**
- Create: `cli/pyproject.toml`
- Create: `cli/seeforce_cli/__init__.py`
- Create: `cli/seeforce_cli/main.py`
- Create: `cli/tests/__init__.py`

**Interfaces:**
- Consumes: nothing
- Produces: `seeforce --help` works after `uv tool install .`; `seeforce --version` prints `0.1.0`

- [ ] **Step 1: Create cli/pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "seeforce"
version = "0.1.0"
description = "CLI for SeeForce — validate and publish C4 architecture maps"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "httpx>=0.27",
    "seeforce-c4parser @ git+https://github.com/SilversMind/seeforce.git#subdirectory=packages/c4parser",
    "mcp>=1.0",
]

[project.scripts]
seeforce = "seeforce_cli.main:cli"
seeforce-mcp = "seeforce_cli.mcp_server:main"

[tool.hatch.build.targets.wheel]
packages = ["seeforce_cli"]
```

- [ ] **Step 2: Create cli/seeforce_cli/__init__.py**

```python
```
(empty)

- [ ] **Step 3: Create cli/seeforce_cli/main.py**

```python
import click


@click.group()
@click.version_option(package_name="seeforce")
def cli():
    """SeeForce — validate C4 architecture annotations locally."""
```

- [ ] **Step 4: Create cli/tests/__init__.py**

```python
```
(empty)

- [ ] **Step 5: Install and smoke-test**

```bash
cd cli && uv tool install . --force
seeforce --version
seeforce --help
```

Expected:
```
seeforce, version 0.1.0
Usage: seeforce [OPTIONS] COMMAND [ARGS]...
```

- [ ] **Step 6: Commit**

```bash
git add cli/
git commit -m "feat(cli): scaffold seeforce package"
```

---

### Task 3: Config module

**Files:**
- Create: `cli/seeforce_cli/config.py`
- Create: `cli/tests/test_config.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `config_path() -> Path`
  - `load_config() -> dict` — returns `{"api_url": str, "token": str | None}`
  - `save_config(api_url: str, token: str) -> None`

- [ ] **Step 1: Write failing test**

Create `cli/tests/test_config.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd cli && python -m pytest tests/test_config.py -v
```

Expected: ImportError — module does not exist yet.

- [ ] **Step 3: Create cli/seeforce_cli/config.py**

```python
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
```

- [ ] **Step 4: Run tests**

```bash
cd cli && python -m pytest tests/test_config.py -v
```

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add cli/seeforce_cli/config.py cli/tests/test_config.py
git commit -m "feat(cli): config module — read/write ~/.config/seeforce/config.toml"
```

---

### Task 4: Backend — `/cli/auth/` OAuth view

**Files:**
- Create: `backend/apps/graph/views/cli_auth.py`
- Modify: `backend/apps/graph/urls.py`
- Create: `backend/tests/graph/test_cli_auth.py`

**Interfaces:**
- Consumes: existing Django session auth (GitHub OAuth via allauth); existing DRF `Token` model
- Produces:
  - `GET /cli/auth/?port=PORT&state=STATE` — if authenticated: get-or-create DRF token, redirect to `http://localhost:PORT/callback?token=TOKEN&state=STATE`. If not authenticated: redirect through GitHub login with `next=/cli/auth/?port=PORT&state=STATE`.
  - Response when authentication completes: `302` to `http://localhost:PORT/callback?token=<token>&state=<state>`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/graph/test_cli_auth.py`:

```python
import pytest
from django.urls import reverse
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="pass")


def test_cli_auth_redirects_to_login_when_unauthenticated(client):
    r = client.get("/cli/auth/?port=9876&state=abc123")
    assert r.status_code == 302
    assert "login" in r["Location"] or "github" in r["Location"].lower() or "accounts" in r["Location"]


def test_cli_auth_redirects_to_localhost_when_authenticated(client, user):
    client.force_login(user)
    r = client.get("/cli/auth/?port=9876&state=abc123")
    assert r.status_code == 302
    assert r["Location"].startswith("http://localhost:9876/callback")
    assert "token=" in r["Location"]
    assert "state=abc123" in r["Location"]


def test_cli_auth_creates_token_if_missing(client, user, db):
    assert not Token.objects.filter(user=user).exists()
    client.force_login(user)
    client.get("/cli/auth/?port=9876&state=abc123")
    assert Token.objects.filter(user=user).exists()


def test_cli_auth_rejects_missing_port(client, user):
    client.force_login(user)
    r = client.get("/cli/auth/?state=abc123")
    assert r.status_code == 400


def test_cli_auth_rejects_non_numeric_port(client, user):
    client.force_login(user)
    r = client.get("/cli/auth/?port=evil&state=abc123")
    assert r.status_code == 400
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd backend && python -m pytest tests/graph/test_cli_auth.py -v
```

Expected: 404 errors (URL not registered yet).

- [ ] **Step 3: Create backend/apps/graph/views/cli_auth.py**

```python
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.http import require_GET
from rest_framework.authtoken.models import Token
from urllib.parse import urlencode


@require_GET
def cli_auth(request):
    port = request.GET.get("port", "").strip()
    state = request.GET.get("state", "").strip()

    if not port or not port.isdigit():
        return HttpResponseBadRequest("Missing or invalid 'port' parameter.")

    if not request.user.is_authenticated:
        login_url = settings.LOGIN_URL
        next_url = request.get_full_path()
        return HttpResponseRedirect(f"{login_url}?next={next_url}")

    token, _ = Token.objects.get_or_create(user=request.user)
    params = urlencode({"token": token.key, "state": state})
    return HttpResponseRedirect(f"http://localhost:{port}/callback?{params}")
```

- [ ] **Step 4: Register URL**

In `backend/apps/graph/urls.py`, add before the router include:

```python
from .views.cli_auth import cli_auth

urlpatterns = [
    ...
    path("cli/auth/", cli_auth),
    ...
]
```

Wait — this is under `/api/graph/`. The URL should be at `/cli/auth/` not `/api/graph/cli/auth/`. Register it in `backend/c4_project/urls.py` instead:

```python
from apps.graph.views.cli_auth import cli_auth

urlpatterns = [
    ...
    path("cli/auth/", cli_auth),
]
```

- [ ] **Step 5: Run tests**

```bash
cd backend && python -m pytest tests/graph/test_cli_auth.py -v
```

Expected: 5 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/apps/graph/views/cli_auth.py backend/c4_project/urls.py backend/tests/graph/test_cli_auth.py
git commit -m "feat(api): /cli/auth/ OAuth redirect for CLI login flow"
```

---

### Task 5: `seeforce login` command — localhost OAuth callback

**Files:**
- Create: `cli/seeforce_cli/commands/__init__.py`
- Create: `cli/seeforce_cli/commands/login.py`
- Modify: `cli/seeforce_cli/main.py`
- Create: `cli/tests/test_login.py`

**Interfaces:**
- Consumes: `load_config()`, `save_config(api_url, token)` from `seeforce_cli.config`
- Produces: `seeforce login [--api-url URL]` — opens browser, starts local HTTP server, captures token from OAuth redirect, saves config

- [ ] **Step 1: Write failing test**

Create `cli/tests/test_login.py`:

```python
import json
import threading
import urllib.request
from unittest.mock import patch, MagicMock
import pytest
from click.testing import CliRunner
from seeforce_cli.main import cli


def test_login_saves_config_on_success(tmp_path):
    """Simulate a successful OAuth callback by hitting the local server ourselves."""
    captured = {}

    def fake_open_browser(url):
        # Extract port from url, hit callback ourselves
        import re
        port = int(re.search(r"port=(\d+)", url).group(1))
        state = re.search(r"state=([^&]+)", url).group(1)
        captured["port"] = port
        captured["state"] = state

    config_file = tmp_path / "config.toml"

    with patch("seeforce_cli.commands.login.click.launch", side_effect=fake_open_browser), \
         patch("seeforce_cli.config.config_path", return_value=config_file):

        runner = CliRunner()

        def trigger_callback():
            import time
            time.sleep(0.3)
            port = captured.get("port")
            state = captured.get("state")
            if port:
                urllib.request.urlopen(
                    f"http://localhost:{port}/callback?token=mytoken&state={state}"
                )

        t = threading.Thread(target=trigger_callback)
        t.start()

        result = runner.invoke(cli, ["login", "--api-url", "https://example.com"])
        t.join(timeout=3)

    assert result.exit_code == 0, result.output
    assert "mytoken" in result.output or "Logged in" in result.output
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd cli && python -m pytest tests/test_login.py -v
```

Expected: ImportError or ClickException.

- [ ] **Step 3: Create cli/seeforce_cli/commands/__init__.py**

```python
```
(empty)

- [ ] **Step 4: Create cli/seeforce_cli/commands/login.py**

```python
import http.server
import secrets
import threading
import urllib.parse
from typing import Optional

import click

from seeforce_cli.config import load_config, save_config

_CALLBACK_HTML = b"""<!DOCTYPE html>
<html><body>
<h2>SeeForce CLI authenticated successfully.</h2>
<p>You can close this tab.</p>
</body></html>"""

_received: dict = {}


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        _received["token"] = params.get("token", [None])[0]
        _received["state"] = params.get("state", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(_CALLBACK_HTML)

    def log_message(self, *args):
        pass  # silence request logs


def _find_free_port() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@click.command()
@click.option("--api-url", default=None, help="SeeForce API base URL.")
def login(api_url: Optional[str]):
    """Authenticate with SeeForce via GitHub OAuth."""
    cfg = load_config()
    url = (api_url or cfg["api_url"]).rstrip("/")
    state = secrets.token_urlsafe(16)
    port = _find_free_port()

    _received.clear()
    server = http.server.HTTPServer(("localhost", port), _CallbackHandler)
    server.timeout = 120

    auth_url = f"{url}/cli/auth/?port={port}&state={state}"
    click.echo(f"Opening browser: {auth_url}")
    click.launch(auth_url)
    click.echo("Waiting for authentication... (timeout: 120s)")

    def serve():
        server.handle_request()

    t = threading.Thread(target=serve)
    t.start()
    t.join(timeout=125)
    server.server_close()

    token = _received.get("token")
    returned_state = _received.get("state")

    if not token:
        raise click.ClickException("Authentication timed out or was cancelled.")
    if returned_state != state:
        raise click.ClickException("State mismatch — possible CSRF attempt. Aborting.")

    save_config(url, token)
    click.echo(f"Logged in. Config saved to ~/.config/seeforce/config.toml")
```

- [ ] **Step 5: Register login in main.py**

```python
import click
from seeforce_cli.commands.login import login


@click.group()
@click.version_option(package_name="seeforce")
def cli():
    """SeeForce — validate C4 architecture annotations locally."""


cli.add_command(login)
```

- [ ] **Step 6: Run tests**

```bash
cd cli && python -m pytest tests/test_login.py -v
```

Expected: PASS.

- [ ] **Step 7: Manual smoke-test (requires running backend)**

```bash
seeforce login
```

Expected: browser opens `http://localhost:8000/cli/auth/?port=...`, after GitHub login redirects back, terminal prints "Logged in."

- [ ] **Step 8: Commit**

```bash
git add cli/seeforce_cli/commands/ cli/seeforce_cli/main.py cli/tests/test_login.py
git commit -m "feat(cli): login command — GitHub OAuth localhost callback"
```

---

### Task 6: `seeforce scan` command — local validation only

**Files:**
- Create: `cli/seeforce_cli/commands/scan.py`
- Modify: `cli/seeforce_cli/main.py`
- Create: `cli/tests/test_scan.py`

**Interfaces:**
- Consumes: `c4parser.scan(root_path, extensions, excludes) -> list[C4Element]`; `c4parser.build(elements) -> dict`; `c4parser.export_workspace(workspace) -> str`
- Produces: `seeforce scan [PATH]` — scans directory, prints summary of found elements + validation errors, writes `workspace.json` to PATH

- [ ] **Step 1: Write failing tests**

Create `cli/tests/test_scan.py`:

```python
import textwrap
import json
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
    _write_annotated_repo(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["scan", str(tmp_path)])
    ws_file = tmp_path / "workspace.json"
    assert ws_file.exists()
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
    assert not (tmp_path / "workspace.json").exists()
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd cli && python -m pytest tests/test_scan.py -v
```

Expected: ImportError or command not found.

- [ ] **Step 3: Create cli/seeforce_cli/commands/scan.py**

```python
import json
import sys
from pathlib import Path
from typing import Optional

import click
import c4parser
from c4parser.exceptions import C4ParseError, C4ValidationError


@click.command()
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False))
@click.option("--dry-run", is_flag=True, help="Print workspace JSON without writing file.")
@click.option("--output", "-o", default=None, help="Output file path (default: <path>/workspace.json).")
def scan(path: str, dry_run: bool, output: Optional[str]):
    """Scan PATH for C4 annotations and validate the workspace."""
    root = Path(path).resolve()

    click.echo(f"Scanning {root}...")
    try:
        elements = c4parser.scan(str(root))
    except C4ParseError as exc:
        raise click.ClickException(str(exc))

    if not elements:
        click.echo("No C4 annotations found.")
        return

    try:
        workspace = c4parser.build(elements)
    except C4ValidationError as exc:
        click.echo(f"Validation error: {exc}", err=True)
        sys.exit(1)

    systems = workspace["model"]["softwareSystems"]
    n_containers = sum(len(s.get("containers", [])) for s in systems)
    n_components = sum(
        len(c.get("components", []))
        for s in systems
        for c in s.get("containers", [])
    )
    click.echo(
        f"Found {len(elements)} elements — "
        f"{len(systems)} system(s), {n_containers} container(s), {n_components} component(s)"
    )
    click.echo(f"Workspace: {workspace['name']}")

    if dry_run:
        click.echo(json.dumps(workspace, indent=2))
        return

    out_path = Path(output) if output else root / "workspace.json"
    out_path.write_text(c4parser.export_workspace(workspace), encoding="utf-8")
    click.echo(f"Written: {out_path}")
```

- [ ] **Step 4: Register scan in main.py**

```python
import click
from seeforce_cli.commands.login import login
from seeforce_cli.commands.scan import scan


@click.group()
@click.version_option(package_name="seeforce")
def cli():
    """SeeForce — validate C4 architecture annotations locally."""


cli.add_command(login)
cli.add_command(scan)
```

- [ ] **Step 5: Run tests**

```bash
cd cli && python -m pytest tests/test_scan.py -v
```

Expected: 5 PASS.

- [ ] **Step 6: Commit**

```bash
git add cli/seeforce_cli/commands/scan.py cli/seeforce_cli/main.py cli/tests/test_scan.py
git commit -m "feat(cli): scan command — local C4 annotation validation + workspace.json output"
```

---

### Task 7: `seeforce mcp install` command

**Files:**
- Create: `cli/seeforce_cli/commands/mcp.py`
- Modify: `cli/seeforce_cli/main.py`
- Create: `cli/tests/test_mcp.py`

**Interfaces:**
- Consumes: `load_config()` from `seeforce_cli.config`
- Produces: `seeforce mcp install [--project-path PATH]` — writes `mcpServers.seeforce` entry into `~/.claude.json`; if `.c4project` is absent in project path, fetches latest project UUID from API and writes it

- [ ] **Step 1: Write failing tests**

Create `cli/tests/test_mcp.py`:

```python
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
```

- [ ] **Step 2: Run to confirm failure**

```bash
cd cli && python -m pytest tests/test_mcp.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create cli/seeforce_cli/commands/mcp.py**

```python
import json
from pathlib import Path
from typing import Optional

import click
import httpx

from seeforce_cli.config import load_config


def _claude_json_path() -> Path:
    return Path.home() / ".claude.json"


def _load_claude_json(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_claude_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


@click.group()
def mcp():
    """Manage SeeForce MCP server integration."""


@mcp.command("install")
@click.option("--project-path", default=".", type=click.Path(exists=True, file_okay=False),
              help="Project repo path — .c4project written here if absent.")
@click.option("--skip-project-id", is_flag=True, hidden=True,
              help="Skip .c4project fetch (for tests).")
def install(project_path: str, skip_project_id: bool):
    """Install SeeForce MCP server into ~/.claude.json."""
    cfg = load_config()
    if not cfg["token"]:
        raise click.ClickException("Not logged in. Run: seeforce login")

    api_url = cfg["api_url"]
    token = cfg["token"]

    claude_path = _claude_json_path()
    data = _load_claude_json(claude_path)
    data.setdefault("mcpServers", {})

    data["mcpServers"]["seeforce"] = {
        "type": "stdio",
        "command": "uvx",
        "args": ["--from", "seeforce", "seeforce-mcp"],
        "env": {
            "SEEFORCE_API_URL": api_url,
            "SEEFORCE_API_TOKEN": token,
        },
    }
    _save_claude_json(claude_path, data)
    click.echo(f"Written MCP entry 'seeforce' to {claude_path}")

    if not skip_project_id:
        proj = Path(project_path).resolve()
        c4file = proj / ".c4project"
        if c4file.exists():
            click.echo(f".c4project already exists: {c4file.read_text().strip()}")
        else:
            try:
                r = httpx.get(f"{api_url}/api/graph/", headers={"Authorization": f"Token {token}"}, timeout=10)
                r.raise_for_status()
                projects = r.json()
            except Exception as exc:
                click.echo(f"Warning: could not fetch projects ({exc}). Run 'seeforce mcp install' again after syncing.")
                projects = []

            if projects:
                latest = sorted(projects, key=lambda p: p.get("updated_at", ""), reverse=True)[0]
                uuid = latest.get("project_id") or str(latest["id"])
                c4file.write_text(uuid)
                click.echo(f"Written .c4project ({uuid}) to {proj}")
            else:
                click.echo("No projects on server yet — import a repo in SeeForce first, then re-run this command.")

    click.echo("\nRestart Claude Code (or start a new session) to activate the MCP server.")
```

- [ ] **Step 4: Register mcp in main.py**

```python
import click
from seeforce_cli.commands.login import login
from seeforce_cli.commands.scan import scan
from seeforce_cli.commands.mcp import mcp


@click.group()
@click.version_option(package_name="seeforce")
def cli():
    """SeeForce — validate C4 architecture annotations locally."""


cli.add_command(login)
cli.add_command(scan)
cli.add_command(mcp)
```

- [ ] **Step 5: Run tests**

```bash
cd cli && python -m pytest tests/test_mcp.py -v
```

Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add cli/seeforce_cli/commands/mcp.py cli/seeforce_cli/main.py cli/tests/test_mcp.py
git commit -m "feat(cli): mcp install command — write Claude Code MCP config"
```

---

### Task 8: `seeforce-mcp` entry point — self-contained MCP stdio server

**Files:**
- Create: `cli/seeforce_cli/mcp_config.py`
- Create: `cli/seeforce_cli/mcp_client.py`
- Create: `cli/seeforce_cli/mcp_workspace.py`
- Create: `cli/seeforce_cli/mcp_ownership.py`
- Create: `cli/seeforce_cli/mcp_server.py`

**Interfaces:**
- Consumes: `SEEFORCE_API_URL`, `SEEFORCE_API_TOKEN` env vars; `.c4project` in CWD
- Produces: `seeforce-mcp` stdio binary exposing 4 tools: `get_context`, `find_component`, `get_file_owner`, `get_architecture_for_files`

These files are verbatim ports of `mcp/config.py`, `mcp/client.py`, `mcp/workspace.py`, `mcp/ownership.py`, `mcp/server.py` — only import paths change.

- [ ] **Step 1: Create cli/seeforce_cli/mcp_config.py**

Port of `mcp/config.py` — identical logic, no import changes needed (uses only stdlib + os):

```python
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
```

- [ ] **Step 2: Create cli/seeforce_cli/mcp_client.py**

Port of `mcp/client.py`, import from `seeforce_cli.mcp_config`:

```python
import httpx
from seeforce_cli.mcp_config import API_URL, http_headers, resolve_project_id


async def fetch_workspace() -> dict:
    project_id = resolve_project_id()
    async with httpx.AsyncClient(base_url=API_URL, headers=http_headers(), timeout=15) as client:
        if project_id:
            r = await client.get("/api/graph/")
            r.raise_for_status()
            projects = r.json()
            if not isinstance(projects, list):
                projects = [projects]
            match_meta = next((p for p in projects if p.get("project_id") == project_id), None)
            if not match_meta and projects:
                match_meta = projects[0]
            if not match_meta:
                raise ValueError(f"No project found with id {project_id!r}")
            r2 = await client.get(f"/api/graph/{match_meta['id']}/")
            r2.raise_for_status()
            data = r2.json()
        else:
            r = await client.get("/api/graph/latest/")
            r.raise_for_status()
            data = r.json()
    return data.get("source_json", {})
```

- [ ] **Step 3: Create cli/seeforce_cli/mcp_workspace.py**

Port of `mcp/workspace.py` verbatim — uses only stdlib, no import changes needed. Copy the file as-is.

- [ ] **Step 4: Create cli/seeforce_cli/mcp_ownership.py**

Port of `mcp/ownership.py`, change imports:

```python
# Replace:
#   from workspace import all_components, all_containers, all_systems, format_rel
# With:
from seeforce_cli.mcp_workspace import all_components, all_containers, format_rel
```

All other logic identical.

- [ ] **Step 5: Create cli/seeforce_cli/mcp_server.py**

Port of `mcp/server.py`, change imports:

```python
import asyncio
from mcp.server.mcpserver import MCPServer
from seeforce_cli.mcp_client import fetch_workspace
from seeforce_cli.mcp_ownership import infer_owner, render_owner
from seeforce_cli.mcp_workspace import all_components, all_containers, all_systems, external_systems, format_rel

server = MCPServer("SeeForce")

# Copy all 4 tool definitions verbatim from mcp/server.py:
# - get_context
# - find_component
# - get_file_owner
# - get_architecture_for_files


def main():
    asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Reinstall CLI with mcp dep**

```bash
cd cli && uv tool install . --force
```

- [ ] **Step 7: Smoke-test MCP entry point**

```bash
SEEFORCE_API_TOKEN=<token> echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | seeforce-mcp
```

Expected: JSON response with `tools` array listing `get_context`, `find_component`, `get_file_owner`, `get_architecture_for_files`.

- [ ] **Step 8: Commit**

```bash
git add cli/seeforce_cli/mcp_*.py
git commit -m "feat(cli): seeforce-mcp entry point — self-contained MCP stdio server"
```

---

### Task 9: `install.sh` + serve at `/install.sh`

**Files:**
- Create: `install.sh` (repo root)
- Create: `backend/apps/graph/views/install.py`
- Modify: `backend/c4_project/urls.py`
- Create: `backend/tests/graph/test_install_sh.py`

**Interfaces:**
- Consumes: nothing
- Produces: `GET /install.sh` → returns shell script content; script installs uv then `seeforce` CLI

- [ ] **Step 1: Create install.sh**

```bash
#!/bin/sh
# SeeForce CLI installer
# Usage: curl -fsSL https://seeforce.onrender.com/install.sh | sh
set -e

REPO="https://github.com/SilversMind/seeforce.git"
PKG="git+${REPO}#subdirectory=cli"

echo "Installing SeeForce CLI..."

if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found — installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

uv tool install "$PKG" --force

echo ""
echo "SeeForce CLI installed. Run: seeforce --help"
echo ""
echo "Get started:"
echo "  1. seeforce login"
echo "  2. seeforce scan ."
echo "  3. seeforce mcp install"
```

- [ ] **Step 2: Write failing test**

Create `backend/tests/graph/test_install_sh.py`:

```python
import pytest


def test_install_sh_served(client):
    r = client.get("/install.sh")
    assert r.status_code == 200
    assert b"uv tool install" in r.content
    assert r["Content-Type"].startswith("text/plain")


def test_install_sh_contains_seeforce_repo(client):
    r = client.get("/install.sh")
    assert b"SilversMind/seeforce" in r.content
```

- [ ] **Step 3: Run to confirm failure**

```bash
cd backend && python -m pytest tests/graph/test_install_sh.py -v
```

Expected: 404 — URL not registered.

- [ ] **Step 4: Create backend/apps/graph/views/install.py**

```python
from pathlib import Path
from django.http import FileResponse, Http404, HttpResponse


_INSTALL_SH = Path(__file__).parents[5] / "install.sh"


def serve_install_sh(request):
    if not _INSTALL_SH.exists():
        raise Http404("install.sh not found")
    content = _INSTALL_SH.read_bytes()
    return HttpResponse(content, content_type="text/plain; charset=utf-8")
```

- [ ] **Step 5: Register URL in backend/c4_project/urls.py**

```python
from apps.graph.views.install import serve_install_sh

urlpatterns = [
    ...
    path("install.sh", serve_install_sh),
    ...
]
```

- [ ] **Step 6: Run tests**

```bash
cd backend && python -m pytest tests/graph/test_install_sh.py -v
```

Expected: 2 PASS.

- [ ] **Step 7: End-to-end install test**

```bash
sh install.sh
seeforce --version
```

Expected: `seeforce, version 0.1.0`

- [ ] **Step 8: Commit**

```bash
git add install.sh backend/apps/graph/views/install.py backend/c4_project/urls.py backend/tests/graph/test_install_sh.py
git commit -m "feat: install.sh shell installer served at /install.sh"
```

---

## Self-Review

### Spec coverage

| Requirement | Task |
|-------------|------|
| Shared `c4parser` package — no duplication | 1 |
| Backend re-exports — existing tests unchanged | 1 |
| `seeforce` package scaffold | 2 |
| Config file read/write | 3 |
| `seeforce login` — GitHub OAuth localhost callback | 4 (backend view) + 5 (CLI command) |
| `seeforce scan .` — local validation, write workspace.json | 6 |
| `seeforce mcp install` — write ~/.claude.json | 7 |
| `seeforce-mcp` entry point — MCP stdio server | 8 |
| `install.sh` served at `/install.sh` | 9 |
| Branch-based preview — no new work needed | GitHub import already supports `github_branch` |
| CLI never pushes workspace to API | enforced by design (scan command has no httpx calls) |

### Placeholder scan

Task 8 step 5: executor must copy all 4 tool bodies verbatim from `mcp/server.py` (lines 48–183). Do not summarize or shorten — copy exactly.

Task 8 step 3: copy `mcp/workspace.py` verbatim — check that it uses no non-stdlib imports beyond what the CLI package already has.

### Type consistency

- `c4parser.scan()` → `list[C4Element]` — same in Task 1 (shared package) and Task 6 (consumer)
- `c4parser.build(elements)` → `dict` — same in Task 6
- `c4parser.export_workspace(ws)` → `str` — same in Task 6
- `load_config()` → `{"api_url": str, "token": str | None}` — Task 3 definition, consumed by Tasks 5, 7, 8
