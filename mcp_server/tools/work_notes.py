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
) -> dict[str, Any]:
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


@mcp.tool()
async def add_work_note(
    incident_number: str,
    created_by: str,
    note_type: str,
    body: str,
) -> dict[str, Any]:
    """Add a work note to an Incident in itsm-api.

    `created_by` accepts any value — `customer`, any agent name, or `assist` — with no identity
    check; this tool performs no authorship guard by design (see this repo's constitution,
    "MCP tools stay unguarded"). `note_type` is validated for presence and type only here; its
    domain-value membership (`comment`/`work_note`/`state_change`/`proposal_sent`) is validated
    by itsm-api, which returns 422 for an invalid value. `incident_number`, `created_by`,
    `note_type`, and `body` are all required — a call missing any of them fails schema validation
    before any HTTP request is made.
    """
    client = _client()
    try:
        return await client.add_work_note(incident_number, created_by, note_type, body)
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
