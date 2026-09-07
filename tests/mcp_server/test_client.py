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


@pytest.mark.anyio
async def test_create_incident_sends_all_six_required_fields_and_returns_created_incident():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/incidents"
        import json as _json
        body = _json.loads(request.content)
        assert body == {
            "account_id": "ACCOUNT-1001", "category": "billing",
            "short_description": "Invoice mismatch", "description": "Customer reports a mismatch.",
            "state": "new", "priority": 2,
        }
        return httpx.Response(201, json={**_SAMPLE_INCIDENT, "number": "TICKET-004500"})

    result = await _client(handler).create_incident(
        account_id="ACCOUNT-1001", category="billing",
        short_description="Invoice mismatch", description="Customer reports a mismatch.",
        state="new", priority=2,
    )
    assert result["number"] == "TICKET-004500"


@pytest.mark.anyio
async def test_create_incident_invalid_category_raises_upstream_error_for_422():
    def handler(request):
        return httpx.Response(
            422,
            json={
                "message": "category must be one of: receiving, putaway, picking, cycle-count, "
                           "billing, integrations, auth, reporting",
                "code": "VALIDATION_ERROR",
            },
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).create_incident(
            account_id="ACCOUNT-1001", category="not-a-real-category",
            short_description="x", description="y", state="new", priority=2,
        )
    assert exc_info.value.status_code == 422


@pytest.mark.anyio
async def test_update_incident_sends_only_provided_mutable_fields_and_returns_result():
    def handler(request):
        assert request.method == "PATCH"
        assert request.url.path == "/incidents/TICKET-004417"
        import json as _json
        body = _json.loads(request.content)
        assert body == {"state": "resolved"}
        assert "number" not in body
        return httpx.Response(200, json={**_SAMPLE_INCIDENT, "state": "resolved"})

    result = await _client(handler).update_incident("TICKET-004417", state="resolved")
    assert result["state"] == "resolved"


@pytest.mark.anyio
async def test_update_incident_unknown_number_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(
            404, json={"message": "Incident TICKET-999999 not found", "code": "INCIDENT_NOT_FOUND"}
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).update_incident("TICKET-999999", state="resolved")
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_update_incident_invalid_state_raises_upstream_error_for_422():
    def handler(request):
        return httpx.Response(
            422,
            json={
                "message": "state must be one of: new, in_progress, on_hold, resolved, closed",
                "code": "VALIDATION_ERROR",
            },
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).update_incident("TICKET-004417", state="not-a-real-state")
    assert exc_info.value.status_code == 422
