import json
from unittest.mock import patch, MagicMock

import requests
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.graph.models import ProjectMap

User = get_user_model()

SAMPLE_WORKSPACE = {
    "name": "test-repo",
    "model": {"people": [], "softwareSystems": []},
    "views": {
        "systemContextViews": [],
        "containerViews": [],
        "componentViews": [],
        "configuration": {"styles": {"elements": [], "relationships": []}},
    },
}


def _mock_github_ok(workspace=None):
    mock = MagicMock()
    mock.ok = True
    mock.status_code = 200
    mock.json.return_value = workspace or SAMPLE_WORKSPACE
    return mock


def _mock_github_404():
    mock = MagicMock()
    mock.ok = False
    mock.status_code = 404
    return mock


def _mock_github_401():
    mock = MagicMock()
    mock.ok = False
    mock.status_code = 401
    return mock


def _mock_github_403():
    mock = MagicMock()
    mock.ok = False
    mock.status_code = 403
    return mock


class ImportFromGitHubTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="importer", password="pass")
        self.client.force_login(self.user)

    def _make_token(self):
        from apps.graph.models import GitHubAppInstallation
        GitHubAppInstallation.objects.create(installation_id="999", user=self.user)
        # Patch at apps.graph.github_app, not apps.graph.views.github_import:
        # _github_token() does `from ..github_app import GitHubAppTokenManager`
        # *inside* the function (matches this file's existing local-import style),
        # so the class is never a module-level attribute of github_import — patch
        # it where it's actually defined instead.
        patcher = patch(
            "apps.graph.github_app.GitHubAppTokenManager.installation_token",
            return_value="ghs-installation-token-abc",
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def _post(self, data):
        return self.client.post(
            "/api/graph/import/github/",
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_unauthenticated_returns_401(self):
        self.client.logout()
        resp = self._post({"repo": "owner/repo"})
        self.assertEqual(resp.status_code, 401)

    def test_missing_repo_returns_400(self):
        self._make_token()
        resp = self._post({"repo": ""})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_invalid_repo_format_returns_400(self):
        self._make_token()
        resp = self._post({"repo": "noslash"})
        self.assertEqual(resp.status_code, 400)

    def test_no_github_token_returns_400(self):
        resp = self._post({"repo": "owner/repo"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("No GitHub App installation found", resp.json()["error"])

    def test_token_minting_failure_returns_400(self):
        # Installation row exists locally, but GitHub rejects the token-mint
        # call (e.g. the installation was revoked on GitHub's side).
        from apps.graph.models import GitHubAppInstallation
        GitHubAppInstallation.objects.create(installation_id="999", user=self.user)
        with patch(
            "apps.graph.github_app.GitHubAppTokenManager.installation_token",
            side_effect=requests.HTTPError("401 Client Error"),
        ):
            resp = self._post({"repo": "owner/repo"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("could not be minted", resp.json()["error"])

    @patch("apps.graph.views.github_import.http_requests.get")
    def test_workspace_not_found_returns_clear_error(self, mock_get):
        self._make_token()
        mock_get.return_value = _mock_github_404()
        resp = self._post({"repo": "owner/repo"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn(".seeforce/workspace.json", resp.json()["error"])
        self.assertIn("just scan", resp.json()["error"])

    @patch("apps.graph.views.github_import.http_requests.get")
    def test_forbidden_private_repo_returns_clear_error(self, mock_get):
        self._make_token()
        mock_get.return_value = _mock_github_403()
        resp = self._post({"repo": "owner/private-repo"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("GitHub App installation", resp.json()["error"])

    @patch("apps.graph.views.github_import.http_requests.get")
    def test_expired_token_returns_clear_error(self, mock_get):
        self._make_token()
        mock_get.return_value = _mock_github_401()
        resp = self._post({"repo": "owner/repo"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("expired", resp.json()["error"])

    @patch("apps.graph.views.github_import.http_requests.get")
    def test_successful_import_creates_project(self, mock_get):
        self._make_token()
        mock_get.return_value = _mock_github_ok()
        resp = self._post({"repo": "owner/repo"})
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertTrue(data["created"])
        pm = ProjectMap.objects.get(id=data["id"])
        self.assertEqual(pm.project_id, "github:owner/repo")
        self.assertEqual(pm.github_repo, "owner/repo")
        self.assertEqual(pm.github_branch, "main")
        self.assertEqual(pm.owner, self.user)

    @patch("apps.graph.views.github_import.http_requests.get")
    def test_reimport_updates_existing_project(self, mock_get):
        self._make_token()
        mock_get.return_value = _mock_github_ok()
        self._post({"repo": "owner/repo"})
        # Re-import same repo
        mock_get.return_value = _mock_github_ok({"name": "updated", "model": {"people": [], "softwareSystems": []}, "views": {"systemContextViews": [], "containerViews": [], "componentViews": [], "configuration": {"styles": {"elements": [], "relationships": []}}}})
        resp = self._post({"repo": "owner/repo"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["created"])
        self.assertEqual(ProjectMap.objects.filter(project_id="github:owner/repo").count(), 1)

    @patch("apps.graph.views.github_import.http_requests.get")
    def test_custom_branch(self, mock_get):
        self._make_token()
        mock_get.return_value = _mock_github_ok()
        resp = self._post({"repo": "owner/repo", "branch": "develop"})
        self.assertEqual(resp.status_code, 201)
        pm = ProjectMap.objects.get(project_id="github:owner/repo")
        self.assertEqual(pm.github_branch, "develop")
        call_url = mock_get.call_args[0][0]
        self.assertIn("ref=develop", call_url)


class SyncFromGitHubTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="syncer", password="pass")
        self.client.force_login(self.user)
        self.pm = ProjectMap.objects.create(
            name="myrepo",
            source_json=SAMPLE_WORKSPACE,
            owner=self.user,
            project_id="github:owner/myrepo",
            github_repo="owner/myrepo",
            github_branch="main",
        )

    def _make_token(self):
        from apps.graph.models import GitHubAppInstallation
        GitHubAppInstallation.objects.create(installation_id="999", user=self.user)
        # Patch at apps.graph.github_app, not apps.graph.views.github_import:
        # _github_token() does `from ..github_app import GitHubAppTokenManager`
        # *inside* the function (matches this file's existing local-import style),
        # so the class is never a module-level attribute of github_import — patch
        # it where it's actually defined instead.
        patcher = patch(
            "apps.graph.github_app.GitHubAppTokenManager.installation_token",
            return_value="ghs-installation-token-abc",
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def _sync(self):
        return self.client.post(f"/api/graph/{self.pm.id}/sync-github/")

    def test_unauthenticated_returns_401(self):
        self.client.logout()
        resp = self._sync()
        self.assertEqual(resp.status_code, 401)

    def test_non_github_project_returns_400(self):
        self._make_token()
        pm = ProjectMap.objects.create(name="local", source_json=SAMPLE_WORKSPACE, owner=self.user)
        resp = self.client.post(f"/api/graph/{pm.id}/sync-github/")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not imported from GitHub", resp.json()["error"])

    def test_other_user_cannot_sync(self):
        other = User.objects.create_user(username="other", password="pass")
        self.client.force_login(other)
        resp = self._sync()
        self.assertEqual(resp.status_code, 403)

    @patch("apps.graph.views.github_import.http_requests.get")
    def test_workspace_gone_after_sync_attempt(self, mock_get):
        self._make_token()
        mock_get.return_value = _mock_github_404()
        resp = self._sync()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("just scan", resp.json()["error"])

    @patch("apps.graph.views.github_import.http_requests.get")
    def test_successful_sync_updates_source_json(self, mock_get):
        self._make_token()
        updated = {**SAMPLE_WORKSPACE, "name": "refreshed"}
        mock_get.return_value = _mock_github_ok(updated)
        resp = self._sync()
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["synced"])
        self.pm.refresh_from_db()
        self.assertEqual(self.pm.source_json["name"], "refreshed")


class LinkToGithubTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="linker", password="pass")
        self.client.force_login(self.user)
        self.pm = ProjectMap.objects.create(
            name="uploaded project",
            source_json=SAMPLE_WORKSPACE,
            owner=self.user,
        )

    def _make_token(self):
        from apps.graph.models import GitHubAppInstallation
        GitHubAppInstallation.objects.create(installation_id="999", user=self.user)
        # Patch at apps.graph.github_app, not apps.graph.views.github_import:
        # _github_token() does `from ..github_app import GitHubAppTokenManager`
        # *inside* the function (matches this file's existing local-import style),
        # so the class is never a module-level attribute of github_import — patch
        # it where it's actually defined instead.
        patcher = patch(
            "apps.graph.github_app.GitHubAppTokenManager.installation_token",
            return_value="ghs-installation-token-abc",
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def _link(self, data):
        return self.client.post(
            f"/api/graph/{self.pm.id}/link-github/",
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_unauthenticated_returns_401(self):
        self.client.logout()
        resp = self._link({"repo": "owner/repo"})
        self.assertEqual(resp.status_code, 401)

    def test_other_user_cannot_link(self):
        other = User.objects.create_user(username="other2", password="pass")
        self.client.force_login(other)
        resp = self._link({"repo": "owner/repo"})
        self.assertEqual(resp.status_code, 403)

    def test_invalid_repo_format_returns_400(self):
        self._make_token()
        resp = self._link({"repo": "not-a-valid-repo"})
        self.assertEqual(resp.status_code, 400)

    def test_already_linked_project_returns_400(self):
        self._make_token()
        self.pm.github_repo = "owner/already"
        self.pm.save(update_fields=["github_repo"])
        resp = self._link({"repo": "owner/other"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already linked", resp.json()["error"])

    def test_repo_already_imported_elsewhere_returns_400(self):
        self._make_token()
        ProjectMap.objects.create(
            name="other project",
            source_json=SAMPLE_WORKSPACE,
            owner=self.user,
            project_id="github:owner/taken",
            github_repo="owner/taken",
            github_branch="main",
        )
        resp = self._link({"repo": "owner/taken"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already imported", resp.json()["error"])

    @patch("apps.graph.views.github_import.http_requests.get")
    def test_successful_link_attaches_repo_in_place(self, mock_get):
        self._make_token()
        mock_get.return_value = _mock_github_ok(SAMPLE_WORKSPACE)
        resp = self._link({"repo": "owner/newrepo", "branch": "develop"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["linked"])
        self.assertEqual(resp.json()["id"], self.pm.id)
        self.pm.refresh_from_db()
        self.assertEqual(self.pm.github_repo, "owner/newrepo")
        self.assertEqual(self.pm.github_branch, "develop")
        self.assertEqual(self.pm.project_id, "github:owner/newrepo")
        # Same row, not a new project.
        self.assertEqual(ProjectMap.objects.count(), 1)
