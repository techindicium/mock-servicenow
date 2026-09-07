from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.client import ItsmApiClient
from mcp_server.config import get_api_base_url
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


def _client() -> ItsmApiClient:
    return ItsmApiClient(get_api_base_url())


@mcp.tool()
async def list_escalations(
    account_id: str | None = None,
    open_only: bool | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> dict[str, Any]:
    """List Escalations known to itsm-api, filtered and paginated per the given arguments.

    With no arguments, returns the full unfiltered result, including any Escalation whose
    `owner` is null — this tool never filters, flags, or annotates ownerless Escalations.
    `page`/`page_size` pass through to GET /escalations pagination, mirroring `list_incidents`.
    """
    client = _client()
    try:
        return await client.list_escalations(
            account_id=account_id, open_only=open_only, page=page, page_size=page_size
        )
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
