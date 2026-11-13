"""
@c3:component
name: GitHub App Token Manager
container: Backend
description: Signs a JWT with the GitHub App's private key and exchanges it for a short-lived (1h) installation access token, used to authenticate GitHub API calls on behalf of one installation instead of a long-lived OAuth token. The token is cached for 50 of its 60 minutes, so a burst of API calls mints once instead of once per call.
short_desc: Mints and caches short-lived GitHub App installation tokens
uses:
  - GitHub: "Signs the app JWT (RS256), reads an installation's owning account via /app/installations/{id}, and exchanges the JWT for a 1h installation access token via /app/installations/{id}/access_tokens"
    technology: HTTPS
"""
import os
import time

import jwt
import requests as http_requests
from django.core.cache import cache

_TOKEN_TTL = 50 * 60


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

    def installation_account(self, installation_id: str) -> dict | None:
        """The GitHub account (user or org) an installation belongs to.
        None if GitHub doesn't know this installation_id."""
        resp = http_requests.get(
            f"https://api.github.com/app/installations/{installation_id}",
            headers={
                "Authorization": f"Bearer {self._app_jwt()}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10,
        )
        if not resp.ok:
            return None
        return resp.json().get("account") or None

    def installation_token(self, installation_id: str) -> str:
        """The installation's access token, minted once per 50 minutes rather than per call."""
        # ponytail: a revoked install keeps serving its cached token until the TTL
        # runs out; forget_installation_token on the setup callback covers reinstalls.
        key = _token_cache_key(installation_id)
        if cached := cache.get(key):
            return cached
        resp = http_requests.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {self._app_jwt()}",
                "Accept": "application/vnd.github+json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        token = resp.json()["token"]
        cache.set(key, token, _TOKEN_TTL)
        return token


def _token_cache_key(installation_id: str) -> str:
    return f"gh:token:{installation_id}"


def forget_installation_token(installation_id: str) -> None:
    """Drop a cached token so the next call mints a fresh one."""
    cache.delete(_token_cache_key(installation_id))
