import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

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
