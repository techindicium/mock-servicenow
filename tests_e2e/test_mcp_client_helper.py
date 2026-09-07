import pytest

from tests_e2e.mcp_client import connect


@pytest.mark.anyio
async def test_connect_yields_an_initialized_session(mcp_dual_server):
    _, mcp_base_url = mcp_dual_server

    async with connect(mcp_base_url) as session:
        result = await session.list_tools()
        names = {tool.name for tool in result.tools}
        assert "list_incidents" in names  # session is usable — initialize() already ran
