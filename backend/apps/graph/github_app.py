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
