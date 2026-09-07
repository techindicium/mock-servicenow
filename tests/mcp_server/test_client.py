import httpx
import pytest

from mcp_server.client import ItsmApiClient
from mcp_server.errors import UpstreamError


def _client(handler):
    return ItsmApiClient("http://itsm-api", transport=httpx.MockTransport(handler))


_SAMPLE_INCIDENT = {
    "number": "TICKET-004417", "account_id": "ACCOUNT-1001", "category": "billing",
    "short_description": "Invoice mismatch", "description": "Customer reports a mismatch.",
    "state": "new", "priority": 2, "opened_at": "2026-09-01T00:00:00Z", "resolved_at": None,
    "assigned_to": None, "assignment_group": "Support Tier 1", "escalated": False,
}


@pytest.mark.anyio
async def test_list_incidents_returns_api_response_unmodified():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/incidents"
        return httpx.Response(200, json={"items": [_SAMPLE_INCIDENT], "page": 1})

    result = await _client(handler).list_incidents()
    assert result == {"items": [_SAMPLE_INCIDENT], "page": 1}


@pytest.mark.anyio
async def test_list_incidents_passes_filters_and_pagination_as_query_params():
    def handler(request):
        params = request.url.params
        assert params["account_id"] == "ACCOUNT-1001"
        assert params["state"] == "new"
        assert params["category"] == "billing"
        assert params["opened_after"] == "2026-08-01"
        assert params["opened_before"] == "2026-09-01"
        assert params["escalated"] == "true"
        assert params["page"] == "2"
        assert params["per_page"] == "50"
        return httpx.Response(200, json={"items": [], "page": 2})

    await _client(handler).list_incidents(
        account_id="ACCOUNT-1001", state="new", category="billing",
        opened_after="2026-08-01", opened_before="2026-09-01", escalated=True,
        page=2, per_page=50,
    )


@pytest.mark.anyio
async def test_get_incident_returns_the_incident():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/incidents/TICKET-004417"
        return httpx.Response(200, json=_SAMPLE_INCIDENT)

    result = await _client(handler).get_incident("TICKET-004417")
    assert result["number"] == "TICKET-004417"


@pytest.mark.anyio
async def test_get_incident_unknown_number_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(
            404,
            json={"message": "Incident TICKET-999999 not found", "code": "INCIDENT_NOT_FOUND"},
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).get_incident("TICKET-999999")
    assert exc_info.value.status_code == 404
    assert exc_info.value.message == "Incident TICKET-999999 not found"
