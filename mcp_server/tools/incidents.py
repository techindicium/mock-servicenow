from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.client import ItsmApiClient
from mcp_server.config import get_api_base_url
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


def _client() -> ItsmApiClient:
    return ItsmApiClient(get_api_base_url())


@mcp.tool()
async def list_incidents(
    account_id: str | None = None,
    state: str | None = None,
    category: str | None = None,
    opened_after: str | None = None,
    opened_before: str | None = None,
    escalated: bool | None = None,
    page: int | None = None,
    per_page: int | None = None,
) -> dict[str, Any]:
    """List Incidents known to itsm-api, filtered and paginated per the given arguments."""
    client = _client()
    try:
        return await client.list_incidents(
            account_id=account_id, state=state, category=category,
            opened_after=opened_after, opened_before=opened_before, escalated=escalated,
            page=page, per_page=per_page,
        )
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()


@mcp.tool()
async def get_incident(number: str) -> dict[str, Any]:
    """Fetch one Incident by number from itsm-api."""
    client = _client()
    try:
        return await client.get_incident(number)
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
