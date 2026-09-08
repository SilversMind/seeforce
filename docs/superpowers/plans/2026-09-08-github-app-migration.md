# GitHub App Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the OAuth App `repo`-scope token used by GitHub Import with a GitHub App installation token, so users grant per-repo access via GitHub's own install UI instead of an all-repos OAuth scope.

**Architecture:** Identity login stays on django-allauth (GitHub OAuth, narrowed to `user:email` only). A new `GitHubAppTokenManager` signs a JWT with the App's private key and exchanges it for a short-lived (1h) installation access token. A new `GitHubAppInstallation` model links a GitHub installation_id to the SeeForce user who installed it, populated by a new `github-app/setup/` redirect endpoint (same shape as the existing `cli/auth/` endpoint). `github_import.py` swaps its OAuth-token lookup for a call to the token manager. No webhook receiver yet — deferred, GitHub App's webhook is left inactive.

**Tech Stack:** Django, django-allauth, PyJWT (RS256, via `cryptography`), DRF for JSON endpoints / plain Django view for the browser redirect (matching `cli_auth.py`).

**Spec:** No separate spec doc — this plan's Background section below captures the decisions, derived from a `/grill-me` conversation on 2026-09-08 that worked through the OAuth-App → GitHub-App tradeoffs, token model, and this codebase's existing auth flow.

## Background

- GitHub App already created: name `SeeForceApp`, App ID `4869602`, installable on "Any account", Repository permissions Contents:Read + Metadata:Read, webhook inactive, Setup URL set to `https://seeforce.onrender.com/github-app/setup/`.
- Secrets already in place: `backend/.env` has `GITHUB_APP_ID`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_APP_PRIVATE_KEY_PATH` (local: `~/.config/seeforce/seeforceapp-private-key.pem`, Render: Secret File path). `*.pem` and `backend/.env` are gitignored.
- CLI (`cli/seeforce_cli/commands/login.py`) needs **no changes** — it only ever exchanges the browser callback for a SeeForce-issued DRF `Token`, never a raw GitHub token. Confirmed by reading `cli_auth.py`, which this plan's new setup endpoint mirrors.
- Existing OAuth App must be revoked/deleted on GitHub once this ships — out of scope for this plan (manual GitHub-side step, not code).

## Global Constraints

- Follow existing flat module layout in `backend/apps/graph/` — no new `services/` subpackage (codebase keeps `models.py`, `transformers.py`, `github_app.py` etc. as siblings, not layered directories).
- Every new/modified backend view file keeps the `@c3:component` docstring annotation convention already used in `views/auth.py`, `views/github_import.py`, `views/graph.py`.
- `models.py` itself stays unannotated (matches current state) — `Database` edges are declared in the view file that touches the model, not in `models.py`.
- No caching/Redis for installation tokens — minted fresh per call. Not a hot path (manual import/sync clicks), no measured need yet.
- No webhook code in this plan — GitHub App webhook stays inactive.

---

## File Structure

- `backend/pyproject.toml` — add `pyjwt[crypto]` dependency.
- `backend/apps/graph/github_app.py` **(new)** — `GitHubAppTokenManager`: signs the App JWT, mints installation access tokens.
- `backend/tests/graph/test_github_app.py` **(new)** — tests for `GitHubAppTokenManager`.
- `backend/apps/graph/models.py` **(modify)** — add `GitHubAppInstallation` model.
- `backend/apps/graph/views/github_app.py` **(new)** — `github_app_setup` view, links `installation_id` to the logged-in user.
- `backend/tests/graph/test_github_app_setup.py` **(new)** — tests for the setup endpoint.
- `backend/c4_project/urls.py` **(modify)** — wire `github-app/setup/`.
- `backend/apps/graph/views/github_import.py` **(modify)** — swap `_github_token` (OAuth `SocialToken`) for an installation-token lookup.
- `backend/tests/graph/test_github_import.py` **(modify)** — update the token fixture used by every test in this file.
- `backend/c4_project/settings/base.py` **(modify)** — narrow `SCOPE` from `["user:email", "repo"]` to `["user:email"]`.

---

## Task 1: GitHubAppTokenManager — JWT signing + installation token minting

**Files:**
- Modify: `backend/pyproject.toml`
- Create: `backend/apps/graph/github_app.py`
- Test: `backend/tests/graph/test_github_app.py`

**Interfaces:**
- Produces: `GitHubAppTokenManager()` — reads `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY_PATH` from `os.environ` in `__init__`. Public method `installation_token(installation_id: str) -> str`, returns the minted token string. Internal `_app_jwt() -> str`.

- [ ] **Step 1: Add the dependency**

In `backend/pyproject.toml`, add to `dependencies`:

```toml
    "pyjwt[crypto]>=2.8",
```

Run: `cd backend && uv sync --extra dev` (repo uses `uv`; `--extra dev` is required to get `pytest`/`pytest-django` — `uv sync` alone won't install them, confirmed by running the baseline suite in this worktree)

Note: `pyjwt[crypto]==2.13.0` is already present in `backend/uv.lock` as a transitive dependency (of `mcp`), so this step won't download anything new — it just promotes it to a direct, explicit dependency, which is the right call regardless (don't rely on another package's transitive dep for something we use directly and permanently).

- [ ] **Step 2: Write the failing test for `_app_jwt`**

```python
# backend/tests/graph/test_github_app.py
import time

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from apps.graph.github_app import GitHubAppTokenManager


@pytest.fixture
def rsa_private_key_path(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path = tmp_path / "test-key.pem"
    path.write_bytes(pem)
    return path, key


@pytest.fixture
def manager(monkeypatch, rsa_private_key_path):
    path, _key = rsa_private_key_path
    monkeypatch.setenv("GITHUB_APP_ID", "4869602")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(path))
    return GitHubAppTokenManager()


def test_app_jwt_is_signed_with_correct_claims(manager, rsa_private_key_path):
    _path, key = rsa_private_key_path
    public_key = key.public_key()

    token = manager._app_jwt()

    decoded = jwt.decode(token, public_key, algorithms=["RS256"])
    assert decoded["iss"] == "4869602"
    now = int(time.time())
    assert decoded["iat"] <= now
    assert decoded["exp"] - decoded["iat"] == 660
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/graph/test_github_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'apps.graph.github_app'`

- [ ] **Step 4: Write `GitHubAppTokenManager`**

```python
# backend/apps/graph/github_app.py
"""
@c3:component
name: GitHub App Token Manager
container: Backend
description: Signs a JWT with the GitHub App's private key and exchanges it for a short-lived (1h) installation access token, used to authenticate GitHub API calls on behalf of one installation instead of a long-lived OAuth token.
uses:
  - GitHub: "Signs the app JWT (RS256) and exchanges it for a 1h installation access token via /app/installations/{id}/access_tokens"
    technology: HTTPS
"""
import os
import time

import jwt
import requests as http_requests


class GitHubAppTokenManager:
    def __init__(self):
        self.app_id = os.environ["GITHUB_APP_ID"]
        self.private_key_path = os.environ["GITHUB_APP_PRIVATE_KEY_PATH"]

    def _app_jwt(self) -> str:
        with open(self.private_key_path) as f:
            private_key = f.read()
        now = int(time.time())
        payload = {"iat": now - 60, "exp": now + 600, "iss": self.app_id}
        return jwt.encode(payload, private_key, algorithm="RS256")

    def installation_token(self, installation_id: str) -> str:
        resp = http_requests.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {self._app_jwt()}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["token"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/graph/test_github_app.py -v`
Expected: PASS

- [ ] **Step 6: Write the failing test for `installation_token`**

Append to `backend/tests/graph/test_github_app.py`:

```python
from unittest.mock import MagicMock, patch


def test_installation_token_calls_github_and_returns_token(manager):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"token": "ghs_abc123"}
    with patch.object(manager, "_app_jwt", return_value="fake.jwt.token"), \
         patch("apps.graph.github_app.http_requests.post", return_value=mock_resp) as mock_post:
        token = manager.installation_token("999")

    assert token == "ghs_abc123"
    mock_post.assert_called_once_with(
        "https://api.github.com/app/installations/999/access_tokens",
        headers={
            "Authorization": "Bearer fake.jwt.token",
            "Accept": "application/vnd.github+json",
        },
        timeout=10,
    )
```

- [ ] **Step 7: Run test to verify it fails, then confirm it passes with no further code changes**

Run: `cd backend && uv run pytest tests/graph/test_github_app.py -v`
Expected: this new test should PASS immediately — `installation_token` was already written in Step 4. If it fails, fix `installation_token` to match the assertions above.

- [ ] **Step 8: Commit**

```bash
git add backend/pyproject.toml backend/apps/graph/github_app.py backend/tests/graph/test_github_app.py
git commit -m "feat: add GitHubAppTokenManager for App JWT signing and installation tokens"
```

---

## Task 2: GitHubAppInstallation model

**Files:**
- Modify: `backend/apps/graph/models.py`
- Test: `backend/tests/graph/test_models.py`

**Interfaces:**
- Produces: `GitHubAppInstallation` model with fields `installation_id` (unique `CharField`), `account_login` (`CharField`, blank-ok), `user` (FK to `AUTH_USER_MODEL`, `related_name="github_app_installations"`), `created_at`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/graph/test_models.py` (check the file's existing imports first and match its `User`/`db` fixture style before pasting):

```python
def test_github_app_installation_str_and_uniqueness(db):
    from django.contrib.auth import get_user_model
    from apps.graph.models import GitHubAppInstallation

    User = get_user_model()
    user = User.objects.create_user(username="installer", password="pass")

    install = GitHubAppInstallation.objects.create(
        installation_id="12345", user=user, account_login="SilversMind"
    )
    assert str(install) == "installation:12345 (installer)"
    assert user.github_app_installations.count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/graph/test_models.py -k github_app_installation -v`
Expected: FAIL with `ImportError: cannot import name 'GitHubAppInstallation'`

- [ ] **Step 3: Add the model**

In `backend/apps/graph/models.py`, append:

```python
class GitHubAppInstallation(models.Model):
    installation_id = models.CharField(max_length=32, unique=True, db_index=True)
    account_login = models.CharField(max_length=255, blank=True, default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="github_app_installations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"installation:{self.installation_id} ({self.user})"
```

- [ ] **Step 4: Generate and apply the migration**

Run: `cd backend && uv run python manage.py makemigrations graph`
Expected: creates `apps/graph/migrations/0009_githubappinstallation.py`

Run: `cd backend && uv run python manage.py migrate`
Expected: applies cleanly.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && uv run pytest tests/graph/test_models.py -k github_app_installation -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/graph/models.py backend/apps/graph/migrations/0009_githubappinstallation.py backend/tests/graph/test_models.py
git commit -m "feat: add GitHubAppInstallation model"
```

---

## Task 3: Setup endpoint — link installation_id to the logged-in user

**Files:**
- Create: `backend/apps/graph/views/github_app.py`
- Modify: `backend/c4_project/urls.py`
- Test: `backend/tests/graph/test_github_app_setup.py`

**Interfaces:**
- Consumes: `GitHubAppInstallation` model from Task 2 (`installation_id`, `user`, `account_login`).
- Produces: `github_app_setup(request)` view, mounted at `github-app/setup/`. Unauthenticated → 302 to `/accounts/github/login/?next=...` (same pattern as `cli_auth`). Missing `installation_id` → 400. Otherwise → creates/updates the row, 302 to `settings.LOGIN_REDIRECT_URL`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/graph/test_github_app_setup.py
import pytest
from django.contrib.auth import get_user_model

from apps.graph.models import GitHubAppInstallation

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="installer", password="pass")


def test_setup_redirects_to_login_when_unauthenticated(client):
    r = client.get("/github-app/setup/?installation_id=12345")
    assert r.status_code == 302
    assert "login" in r["Location"] or "github" in r["Location"].lower() or "accounts" in r["Location"]


def test_setup_rejects_missing_installation_id(client, user):
    client.force_login(user)
    r = client.get("/github-app/setup/")
    assert r.status_code == 400


def test_setup_creates_installation_row(client, user):
    client.force_login(user)
    r = client.get("/github-app/setup/?installation_id=12345&setup_action=install")
    assert r.status_code == 302
    install = GitHubAppInstallation.objects.get(installation_id="12345")
    assert install.user == user


def test_setup_updates_existing_installation_owner(client, user, db):
    other = User.objects.create_user(username="other", password="pass")
    GitHubAppInstallation.objects.create(installation_id="12345", user=other)

    client.force_login(user)
    client.get("/github-app/setup/?installation_id=12345")

    install = GitHubAppInstallation.objects.get(installation_id="12345")
    assert install.user == user
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/graph/test_github_app_setup.py -v`
Expected: FAIL — `404` on the not-yet-routed URL.

- [ ] **Step 3: Write the view**

```python
# backend/apps/graph/views/github_app.py
"""
@c3:component
name: GitHub App Token Manager
container: Backend
description: Receives GitHub's post-install/post-update redirect and links the installation_id to the logged-in SeeForce user.
uses:
  - Database: "creates or updates the GitHubAppInstallation row for the logged-in user"
"""
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.views.decorators.http import require_GET

from ..models import GitHubAppInstallation


@require_GET
def github_app_setup(request):
    if not request.user.is_authenticated:
        next_url = request.get_full_path()
        return HttpResponseRedirect(f"/accounts/github/login/?{urlencode({'next': next_url})}")

    installation_id = request.GET.get("installation_id", "").strip()
    if not installation_id:
        return HttpResponseBadRequest("Missing 'installation_id' parameter.")

    GitHubAppInstallation.objects.update_or_create(
        installation_id=installation_id,
        defaults={"user": request.user},
    )
    return HttpResponseRedirect(settings.LOGIN_REDIRECT_URL)
```

- [ ] **Step 4: Wire the URL**

In `backend/c4_project/urls.py`, add the import and route:

```python
from apps.graph.views.github_app import github_app_setup
```

```python
    path("github-app/setup/", github_app_setup),
```
(add both near the existing `cli_auth` import/route, same style)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/graph/test_github_app_setup.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/graph/views/github_app.py backend/c4_project/urls.py backend/tests/graph/test_github_app_setup.py
git commit -m "feat: add GitHub App installation setup endpoint"
```

---

## Task 4: Swap GitHub Import to use installation tokens

**Files:**
- Modify: `backend/apps/graph/views/github_import.py`
- Modify: `backend/tests/graph/test_github_import.py`

**Interfaces:**
- Consumes: `GitHubAppTokenManager.installation_token(installation_id)` from Task 1, `GitHubAppInstallation` from Task 2 (`user.github_app_installations`).

- [ ] **Step 1: Update the test fixture that every test in the file depends on**

In `backend/tests/graph/test_github_import.py`, replace the `_make_token` helper (currently creates an allauth `SocialToken`) with one that creates a `GitHubAppInstallation` and mocks the token manager:

```python
def _make_token(self):
    from apps.graph.models import GitHubAppInstallation
    GitHubAppInstallation.objects.create(installation_id="999", user=self.user)
    patcher = patch(
        "apps.graph.views.github_import.GitHubAppTokenManager.installation_token",
        return_value="ghs-installation-token-abc",
    )
    self.addCleanup(patcher.stop)
    patcher.start()
```

This replaces the old body (`SocialApp`/`SocialAccount`/`SocialToken` creation) — same method name, same call sites in every test in the file, so no other test line changes.

Also update `test_no_github_token_returns_400` — it currently relies on no `SocialToken` existing; with the new lookup it should instead rely on no `GitHubAppInstallation` existing for the user, which is already true when `_make_token()` is not called. No change needed to that test.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/graph/test_github_import.py -v`
Expected: FAIL — `GitHubAppTokenManager` not yet imported in `github_import.py`, and the old `_github_token` still reads `SocialToken` (mock target doesn't exist yet).

- [ ] **Step 3: Swap the token lookup in the view**

In `backend/apps/graph/views/github_import.py`:

Replace the docstring:

```python
"""
@c3:component
name: GitHub Import
container: Backend
description: Imports, re-syncs, and links project architecture to GitHub repositories — fetches .seeforce/workspace.json via the GitHub Contents API using an installation access token minted by the GitHub App Token Manager, and stores it as a ProjectMap. The clickable GitHub blob links themselves are built client-side from github_repo/github_branch, not here.
uses:
  - GitHub: "Fetches .seeforce/workspace.json via GitHub Contents API using an installation access token"
    technology: HTTPS
  - GitHub App Token Manager: "Requests a fresh installation token before each Contents API call"
  - Database: "creates or updates the ProjectMap row for the imported, synced, or linked repo"
"""
```

Replace `_github_token`:

```python
def _github_token(user):
    from ..github_app import GitHubAppTokenManager
    installation = user.github_app_installations.order_by("-created_at").first()
    if installation is None:
        return None
    return GitHubAppTokenManager().installation_token(installation.installation_id)
```

Update the two error-message strings that reference the old OAuth flow (lines currently reading `"GitHub token expired or lacks repo access. Log out and log back in."` and `"...make sure you granted repo access during login."` and `"GitHub account not connected. Log out and log back in with GitHub."`) to match the install flow:

```python
    if resp.status_code == 401:
        raise ValueError("GitHub App installation token expired or invalid. Reinstall the GitHub App.")
    if resp.status_code == 403:
        raise ValueError(
            f"Access denied to {repo}. Make sure this repo is included in your GitHub App installation."
        )
```

And, in the three view functions (`import_from_github`, `link_to_github`, `sync_from_github`), update the "not connected" error message:

```python
    token = _github_token(request.user)
    if not token:
        return Response(
            {"error": "No GitHub App installation found. Install the GitHub App to grant repo access."},
            status=status.HTTP_400_BAD_REQUEST,
        )
```

(same replacement in all three places `_github_token` is checked)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/graph/test_github_import.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/graph/views/github_import.py backend/tests/graph/test_github_import.py
git commit -m "feat: use GitHub App installation tokens instead of OAuth SocialToken in GitHub Import"
```

---

## Task 5: Narrow the identity OAuth scope

**Files:**
- Modify: `backend/c4_project/settings/base.py`

- [ ] **Step 1: Narrow the scope**

In `backend/c4_project/settings/base.py`, change:

```python
SOCIALACCOUNT_PROVIDERS = {
    "github": {
        "SCOPE": ["user:email", "repo"],
```

to:

```python
SOCIALACCOUNT_PROVIDERS = {
    "github": {
        "SCOPE": ["user:email"],
```

- [ ] **Step 2: Run the full backend test suite to confirm nothing else depends on the `repo` scope**

Run: `cd backend && uv run pytest -v`
Expected: PASS (grep confirmed no test asserts on `SCOPE` before this plan was written; this step re-verifies against the working tree as it stands after Tasks 1-4).

- [ ] **Step 3: Commit**

```bash
git add backend/c4_project/settings/base.py
git commit -m "fix: narrow GitHub OAuth login scope to user:email now that repo access comes from the GitHub App"
```

---

## Not in this plan (deliberately deferred, discussed and agreed during planning)

- Webhook receiver for `installation` / `installation_repositories` events — GitHub App webhook stays inactive; revisit once there are real users and staleness becomes an actual problem.
- Frontend UI: a "Connect with GitHub" flow that chains identity login → install redirect, and an install-picker/repo-not-covered UX. Backend endpoints from this plan are enough to support it, but the frontend work itself is a separate plan.
- Revoking the old OAuth App on GitHub (Developer Settings → OAuth Apps → delete) — manual, GitHub-side, done at cutover time, not code.
- Rotating `GITHUB_CLIENT_SECRET` in `backend/.env` — the value currently in the file was pasted into a chat conversation; the user should regenerate it independently of this plan.
