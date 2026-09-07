from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.client import ItsmApiClient
from mcp_server.config import get_api_base_url
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


def _client() -> ItsmApiClient:
    return ItsmApiClient(get_api_base_url())


@mcp.tool()
async def list_sla_records(
    incident_number: str | None = None,
    breached: bool | None = None,
    sla_definition: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> dict[str, Any]:
    """List TaskSla records known to itsm-api, filtered and paginated per the given arguments.

    With no arguments, returns the full unfiltered result, including any record where
    `has_breached` is true — this tool never filters, flags, or annotates breached SLA records.
    `sla_definition`'s value-domain (`first_response`/`resolution`) is not validated by this
    tool's own input schema — only presence and type are checked here. An out-of-domain value is
    schema-valid and reaches itsm-api, which rejects it with its own 422, passed through verbatim.
    `page`/`page_size` pass through to GET /sla pagination, mirroring `list_incidents`.
    """
    client = _client()
    try:
        return await client.list_sla_records(
            incident_number=incident_number,
            breached=breached,
            sla_definition=sla_definition,
            page=page,
            page_size=page_size,
        )
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
