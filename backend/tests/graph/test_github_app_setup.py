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
