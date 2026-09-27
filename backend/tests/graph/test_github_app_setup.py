from unittest.mock import MagicMock, patch

import pytest
from allauth.socialaccount.models import SocialAccount
from apps.graph.models import GitHubAppInstallation
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture(autouse=True)
def app_credentials(monkeypatch):
    """GitHubAppTokenManager reads these in __init__ and signs with the key file;
    tests mock only the outbound HTTP call, so stub the signing."""
    monkeypatch.setenv("GITHUB_APP_ID", "4869602")
    monkeypatch.setenv("GITHUB_APP_PRIVATE_KEY_PATH", "/nonexistent/key.pem")
    monkeypatch.setattr(
        "apps.graph.github_app.GitHubAppTokenManager._app_jwt",
        lambda self: "fake.jwt.token",
    )


def _make_user(username, gh_login, gh_uid):
    user = User.objects.create_user(username=username, password="pass")
    SocialAccount.objects.create(
        provider="github", uid=str(gh_uid), user=user, extra_data={"login": gh_login}
    )
    return user


@pytest.fixture
def user(db):
    return _make_user("installer", "installer-gh", 4242)


def _mock_installation(login="installer-gh", account_id=4242, status_code=200):
    resp = MagicMock()
    resp.ok = status_code == 200
    resp.status_code = status_code
    resp.json.return_value = {
        "id": 12345,
        "account": {"login": login, "id": account_id},
    }
    return resp


def _github(resp):
    return patch("apps.graph.github_app.http_requests.get", return_value=resp)


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
    with _github(_mock_installation()):
        r = client.get("/github-app/setup/?installation_id=12345&setup_action=install")
    assert r.status_code == 302
    install = GitHubAppInstallation.objects.get(installation_id="12345")
    assert install.user == user
    assert install.account_login == "installer-gh"


def test_setup_reclaims_own_installation(client, user):
    """The real owner re-running setup updates their own row."""
    GitHubAppInstallation.objects.create(installation_id="12345", user=user)
    client.force_login(user)
    with _github(_mock_installation()):
        r = client.get("/github-app/setup/?installation_id=12345")
    assert r.status_code == 302
    install = GitHubAppInstallation.objects.get(installation_id="12345")
    assert install.user == user
    assert install.account_login == "installer-gh"


def test_setup_rejects_takeover_of_another_users_installation(client, user, db):
    """installation_id is enumerable — a different user must not be able to claim it."""
    attacker = _make_user("attacker", "attacker-gh", 9999)
    GitHubAppInstallation.objects.create(
        installation_id="12345", user=user, account_login="installer-gh"
    )

    client.force_login(attacker)
    # GitHub says installation 12345 belongs to the original owner's account.
    with _github(_mock_installation()):
        r = client.get("/github-app/setup/?installation_id=12345")

    assert r.status_code == 403
    install = GitHubAppInstallation.objects.get(installation_id="12345")
    assert install.user == user


def test_setup_rejects_unknown_installation_id(client, user):
    client.force_login(user)
    with _github(_mock_installation(status_code=404)):
        r = client.get("/github-app/setup/?installation_id=404404")
    assert r.status_code == 400
    assert not GitHubAppInstallation.objects.filter(installation_id="404404").exists()


def test_setup_rejects_user_without_linked_github_account(client, db):
    user = User.objects.create_user(username="nogh", password="pass")
    client.force_login(user)
    with _github(_mock_installation()):
        r = client.get("/github-app/setup/?installation_id=12345")
    assert r.status_code == 403
    assert not GitHubAppInstallation.objects.exists()
