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
    page_size: int | None = None,
) -> dict[str, Any]:
    """List Incidents known to itsm-api, filtered and paginated per the given arguments."""
    client = _client()
    try:
        return await client.list_incidents(
            account_id=account_id, state=state, category=category,
            opened_after=opened_after, opened_before=opened_before, escalated=escalated,
            page=page, page_size=page_size,
        )
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
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


@mcp.tool()
async def create_incident(
    account_id: str,
    category: str,
    short_description: str,
    description: str,
    state: str,
    priority: int,
) -> dict[str, Any]:
    """Create an Incident in itsm-api. All six fields are required; state and priority have no
    default and must be supplied explicitly."""
    client = _client()
    try:
        return await client.create_incident(
            account_id=account_id, category=category, short_description=short_description,
            description=description, state=state, priority=priority,
        )
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()


@mcp.tool()
async def update_incident(
    number: str,
    state: str | None = None,
    priority: int | None = None,
    assigned_to: str | None = None,
    assignment_group: str | None = None,
) -> dict[str, Any]:
    """Update one or more mutable fields on an Incident in itsm-api.

    This call is unconditional: it carries no permission check, no state-transition guard, and no
    inspection of the Incident's SLA or work-note history. It will resolve or close an Incident
    even if its first_response SLA has breached or no customer-facing work note exists. Building
    safety around this tool is the exercise for a consuming track, not this module's job — see
    this repo's constitution Non-Negotiable Principle 5.
    """
    client = _client()
    try:
        return await client.update_incident(
            number, state=state, priority=priority,
            assigned_to=assigned_to, assignment_group=assignment_group,
        )
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
