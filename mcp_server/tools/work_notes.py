from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.client import ItsmApiClient
from mcp_server.config import get_api_base_url
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


def _client() -> ItsmApiClient:
    return ItsmApiClient(get_api_base_url())


@mcp.tool()
async def list_work_notes(
    incident_number: str, page: int | None = None, page_size: int | None = None
) -> list[dict]:
    """List every WorkNote attached to an Incident in itsm-api, unmodified, in chronological
    order. Supports the same page/page_size pagination itsm-api's list endpoints accept."""
    client = _client()
    try:
        return await client.list_work_notes(incident_number, page, page_size)
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
