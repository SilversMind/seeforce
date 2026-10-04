from unittest.mock import AsyncMock, patch

import pytest
from seeforce_cli.mcp_server import get_context, get_static_facts_for_files

_EMPTY_WS = {"model": {"softwareSystems": []}}


@pytest.mark.asyncio
async def test_get_static_facts_for_files_no_facts_message(tmp_path):
    caller = tmp_path / "README.md"
    caller.write_text("# hello\n")
    with patch("seeforce_cli.mcp_server.fetch_workspace", new=AsyncMock(return_value=_EMPTY_WS)):
        result = await get_static_facts_for_files([str(caller)])
    assert "unavailable" in result.lower() or "no facts" in result.lower()


@pytest.mark.asyncio
async def test_get_static_facts_for_files_labels_candidate(tmp_path):
    caller = tmp_path / "service.py"
    caller.write_text('def f():\n    """does a thing"""\n    pass\n')
    with patch("seeforce_cli.mcp_server.fetch_workspace", new=AsyncMock(return_value=_EMPTY_WS)):
        result = await get_static_facts_for_files([str(caller)])
    assert "CANDIDATE" in result
    assert "does a thing" in result


@pytest.mark.asyncio
async def test_get_static_facts_for_files_flattens_multiline_docstring(tmp_path):
    """A multi-line docstring must not spill across output lines — one definition,
    one line. Otherwise a few well-documented files flood the LLM's context."""
    caller = tmp_path / "service.py"
    caller.write_text(
        'def f():\n'
        '    """First line summary.\n'
        '\n'
        '    Args:\n'
        '        amount: the amount to charge.\n'
        '    Returns:\n'
        '        A receipt.\n'
        '    """\n'
        '    pass\n'
    )
    with patch("seeforce_cli.mcp_server.fetch_workspace", new=AsyncMock(return_value=_EMPTY_WS)):
        result = await get_static_facts_for_files([str(caller)])

    assert "First line summary." in result
    assert "Args:" not in result
    assert "A receipt." not in result
    def_lines = [ln for ln in result.splitlines() if ln.startswith("  function f")]
    assert len(def_lines) == 1


@pytest.mark.asyncio
async def test_get_static_facts_for_files_truncates_long_docstring(tmp_path):
    caller = tmp_path / "service.py"
    long_doc = "x" * 400
    caller.write_text(f'def f():\n    """{long_doc}"""\n    pass\n')
    with patch("seeforce_cli.mcp_server.fetch_workspace", new=AsyncMock(return_value=_EMPTY_WS)):
        result = await get_static_facts_for_files([str(caller)])

    def_line = next(ln for ln in result.splitlines() if ln.startswith("  function f"))
    assert len(def_line) < 200
    assert def_line.endswith("…")


@pytest.mark.asyncio
async def test_failed_lookup_names_the_project_and_the_backend():
    """A project-id mismatch used to read like an auth failure — the message must say which id."""
    boom = AsyncMock(side_effect=ValueError("No project found with id 'abc-123'"))
    with patch("seeforce_cli.mcp_server.fetch_workspace", new=boom):
        result = await get_context()
    assert "abc-123" in result
    assert "API_URL" in result


@pytest.mark.asyncio
async def test_project_id_match_ignores_case():
    """GitHub owner/repo is case-insensitive, so .c4project and the backend can disagree on casing."""
    from seeforce_cli.mcp_client import fetch_workspace

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url):
            listing = [{"project_id": "github:SilversMind/seeforce", "id": 1}]
            return _Resp(listing if url == "/api/graph/" else {"source_json": _EMPTY_WS})

    with patch("seeforce_cli.mcp_client.resolve_project_id", return_value="github:Silversmind/seeforce"), \
         patch("seeforce_cli.mcp_client.httpx.AsyncClient", return_value=_Client()):
        assert await fetch_workspace() == _EMPTY_WS
