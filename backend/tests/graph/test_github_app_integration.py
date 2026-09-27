"""End-to-end: GitHub App install redirect -> setup endpoint -> import.

Only the outbound GitHub HTTP calls are mocked (installation-ownership lookup,
token minting, Contents API); the JWT is really signed with a throwaway RSA key.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from allauth.socialaccount.models import SocialAccount
from apps.graph.models import GitHubAppInstallation, ProjectMap
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth import get_user_model

User = get_user_model()

WORKSPACE = {
    "name": "test-repo",
    "model": {"people": [], "softwareSystems": []},
    "views": {
        "systemContextViews": [],
        "containerViews": [],
        "componentViews": [],
        "configuration": {"styles": {"elements": [], "relationships": []}},
    },
}


@pytest.fixture(autouse=True)
def app_credentials(tmp_path, monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_path = tmp_path / "app-key.pem"
    pem_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    monkeypatch.setenv("GITHUB_APP_ID", "4869602")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", str(pem_path))


def _json_response(payload, status_code=200):
    resp = MagicMock()
    resp.ok = status_code < 400
    resp.status_code = status_code
    resp.json.return_value = payload
    return resp


def test_install_then_setup_then_import(client, db):
    user = User.objects.create_user(username="installer", password="pass")
    SocialAccount.objects.create(
        provider="github", uid="4242", user=user, extra_data={"login": "installer-gh"}
    )
    client.force_login(user)

    def fake_get(url, **kwargs):
        if url == "https://api.github.com/app/installations/999":
            return _json_response({"id": 999, "account": {"login": "installer-gh", "id": 4242}})
        if url.startswith("https://api.github.com/repos/installer-gh/myrepo/contents/"):
            return _json_response(WORKSPACE)
        raise AssertionError(f"unexpected GET {url}")

    def fake_post(url, **kwargs):
        assert url == "https://api.github.com/app/installations/999/access_tokens"
        assert kwargs["headers"]["Authorization"].startswith("Bearer ey")  # real signed JWT
        return _json_response({"token": "ghs_installation_token"})

    with patch("requests.get", side_effect=fake_get), patch("requests.post", side_effect=fake_post):
        # 1. GitHub redirects the user back here after installing the App.
        setup = client.get("/github-app/setup/?installation_id=999&setup_action=install")
        assert setup.status_code == 302

        installation = GitHubAppInstallation.objects.get(installation_id="999")
        assert installation.user == user
        assert installation.account_login == "installer-gh"

        # 2. The user imports a repo covered by that installation.
        resp = client.post(
            "/api/graph/import/github/",
            data=json.dumps({"repo": "installer-gh/myrepo"}),
            content_type="application/json",
        )

    assert resp.status_code == 201, resp.content
    pm = ProjectMap.objects.get(id=resp.json()["id"])
    assert pm.github_repo == "installer-gh/myrepo"
    assert pm.owner == user
