"""Real MCP client helper, reused across mock-servicenow's mcp-e2e suite.

Every test in tests_e2e/test_mcp_*_e2e.py connects to a live mcp-server process through this
helper — never by calling a tool function in mcp_server/tools/*.py directly — so every assertion
is made against what a real MCP client received over the real streamable-http transport, per
mcp-e2e.spec.md's Preconditions/Postconditions.

Verified directly against the installed mcp==2.2.0 SDK (inspect against the .venv's
mcp/client/streamable_http.py and mcp/server/mcpserver/exceptions.py) rather than assumed by
analogy with other SDK versions:
  - `streamable_http_client` lives at `mcp.client.streamable_http.streamable_http_client`, is an
    `@asynccontextmanager`, and yields a `(read_stream, write_stream)` 2-tuple.
  - `mcp.ClientSession(read_stream, write_stream)` is itself an async context manager; its
    `initialize()` performs the MCP handshake, `list_tools()` returns `ListToolsResult`, and
    `call_tool(name, arguments)` returns a `CallToolResult` (never raises for a tool-level or
    schema-validation failure — `mcp.server.mcpserver.exceptions.ToolError`'s docstring confirms
    the call returns `is_error=True` with the message in `content` instead).
"""
import contextlib
from collections.abc import AsyncIterator

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

_MCP_PATH = "/mcp"  # mcp SDK's default streamable_http_path (MCPServer.run_streamable_http_async)


@contextlib.asynccontextmanager
async def connect(mcp_base_url: str) -> AsyncIterator[ClientSession]:
    """Connect a real MCP client to a live mcp-server process; yield an initialized session.

    Args:
        mcp_base_url: the base URL start_mcp_server yielded (e.g. "http://127.0.0.1:54232") —
            NOT including the SDK's /mcp path suffix; this helper appends it.

    Yields:
        An initialized mcp.ClientSession, ready for list_tools()/call_tool().
    """
    url = mcp_base_url.rstrip("/") + _MCP_PATH
    async with (
        streamable_http_client(url) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        yield session
