import http.server
import secrets
import threading
import urllib.parse
from typing import Optional

import click

from seeforce_cli.config import load_config, save_config

_CALLBACK_HTML = b"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>SeeForce</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #0f172a;
    color: #f0f6fc;
    font-family: system-ui, -apple-system, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    gap: 1.5rem;
  }
  .check {
    width: 56px; height: 56px;
    background: #166534;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
  }
  .check svg { width: 28px; height: 28px; stroke: #4ade80; stroke-width: 2.5; fill: none; }
  h1 { font-size: 1.5rem; font-weight: 700; }
  p { color: #8b949e; font-size: 0.95rem; }
</style>
</head>
<body>
  <div class="check">
    <svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
  </div>
  <h1>Authenticated</h1>
  <p>You can close this tab and return to your terminal.</p>
</body>
</html>"""

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
