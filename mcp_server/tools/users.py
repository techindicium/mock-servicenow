from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.client import ItsmApiClient
from mcp_server.config import get_api_base_url
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


def _client() -> ItsmApiClient:
    return ItsmApiClient(get_api_base_url())


@mcp.tool()
async def list_users() -> dict[str, Any]:
    """List all SysUsers in itsm-api's support-team directory, unmodified.

    Declares no input parameters. Per BEH-2, any argument at all fails the tool's (strict,
    empty) input schema and errors before this function body — and therefore any HTTP call —
    ever runs.
    """
    client = _client()
    try:
        return await client.list_users()
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
