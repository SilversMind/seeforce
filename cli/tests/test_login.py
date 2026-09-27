import threading
import urllib.request
from unittest.mock import patch

from click.testing import CliRunner
from seeforce_cli.main import cli


def test_login_saves_config_on_success(tmp_path):
    """Simulate a successful OAuth callback by hitting the local server ourselves."""
    captured = {}

    def fake_open_browser(url):
        # Extract port from url, hit callback ourselves
        import re
        port = int(re.search(r"port=(\d+)", url).group(1))
        state = re.search(r"state=([^&]+)", url).group(1)
        captured["port"] = port
        captured["state"] = state

    config_file = tmp_path / "config.toml"

    with patch("seeforce_cli.commands.login.click.launch", side_effect=fake_open_browser), \
         patch("seeforce_cli.config.config_path", return_value=config_file):

        runner = CliRunner()

        def trigger_callback():
            import time
            time.sleep(0.3)
            port = captured.get("port")
            state = captured.get("state")
            if port:
                urllib.request.urlopen(
                    f"http://localhost:{port}/callback?token=mytoken&state={state}"
                )

        t = threading.Thread(target=trigger_callback)
        t.start()

        result = runner.invoke(cli, ["login", "--api-url", "https://example.com"])
        t.join(timeout=3)

    assert result.exit_code == 0, result.output
    assert "mytoken" in result.output or "Logged in" in result.output
