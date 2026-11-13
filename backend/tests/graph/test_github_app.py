import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from apps.graph.github_app import GitHubAppTokenManager, forget_installation_token
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clean_token_cache():
    cache.clear()
    yield
    cache.clear()


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


def _mint(manager, installation_id="999"):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"token": "ghs_abc123"}
    with patch.object(manager, "_app_jwt", return_value="fake.jwt.token"), \
         patch("apps.graph.github_app.http_requests.post", return_value=mock_resp) as mock_post:
        return manager.installation_token(installation_id), mock_post


def test_a_second_call_reuses_the_cached_token_instead_of_minting_again(manager):
    first, _ = _mint(manager)
    second, mock_post = _mint(manager)

    assert first == second == "ghs_abc123"
    mock_post.assert_not_called()


def test_a_reinstall_forgets_the_cached_token(manager):
    _mint(manager)
    forget_installation_token("999")

    _token, mock_post = _mint(manager)

    mock_post.assert_called_once()


def test_each_installation_caches_its_own_token(manager):
    _mint(manager, "999")

    _token, mock_post = _mint(manager, "1000")

    mock_post.assert_called_once()
