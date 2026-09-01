from unittest.mock import AsyncMock, patch

import pytest

from seeforce_cli.mcp_server import get_static_facts_for_files

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
