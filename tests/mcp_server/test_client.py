import httpx
import pytest

from mcp_server.client import ItsmApiClient
from mcp_server.errors import UpstreamError, UpstreamUnreachableError


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
        assert params["page_size"] == "50"
        return httpx.Response(200, json={"items": [], "page": 2})

    await _client(handler).list_incidents(
        account_id="ACCOUNT-1001", state="new", category="billing",
        opened_after="2026-08-01", opened_before="2026-09-01", escalated=True,
        page=2, page_size=50,
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
                "message": "category must be one of: account-opening, payments, cards, "
                           "scheduled-payments, fees, statements, access, "
                           "account-restrictions",
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


# Note: GET /escalations and GET /sla both respond with a paginated envelope
# ({"items": [...], "page", "page_size", "total"}), per app/routers/escalations.py's
# EscalationPage and app/routers/sla.py's PaginatedTaskSla — the same shape list_incidents already
# returns unmodified above. These client methods mirror that: they return response.json()
# verbatim, never unwrapping to a bare list.


@pytest.mark.anyio
async def test_list_escalations_no_args_returns_result_unmodified_including_ownerless():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/escalations"
        assert request.url.params == httpx.QueryParams()
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "number": "ESCALATION-0001",
                        "incident_number": None,
                        "account_id": "ACCOUNT-1001",
                        "summary": "Ownerless escalation",
                        "opened_at": "2026-09-01T00:00:00Z",
                        "closed_at": None,
                        "owner": None,
                    }
                ],
                "page": 1,
                "page_size": 50,
                "total": 1,
            },
        )

    result = await _client(handler).list_escalations()
    assert result["items"][0]["owner"] is None


@pytest.mark.anyio
async def test_list_escalations_forwards_account_id_open_only_and_pagination():
    def handler(request):
        assert dict(request.url.params) == {
            "account_id": "ACCOUNT-1001",
            "open_only": "true",
            "page": "2",
            "page_size": "50",
        }
        return httpx.Response(200, json={"items": [], "page": 2, "page_size": 50, "total": 0})

    await _client(handler).list_escalations(
        account_id="ACCOUNT-1001", open_only=True, page=2, page_size=50
    )


@pytest.mark.anyio
async def test_list_sla_records_no_args_returns_result_unmodified_including_breached():
    def handler(request):
        assert request.url.path == "/sla"
        assert request.url.params == httpx.QueryParams()
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "sys_id": "SLA-0001",
                        "incident_number": "TICKET-000001",
                        "sla_definition": "resolution",
                        "target_minutes": 1440,
                        "actual_minutes": 2000,
                        "has_breached": True,
                        "business_time_only": True,
                    }
                ],
                "page": 1,
                "page_size": 50,
                "total": 1,
            },
        )

    result = await _client(handler).list_sla_records()
    assert result["items"][0]["has_breached"] is True


@pytest.mark.anyio
async def test_list_sla_records_forwards_all_filters_and_pagination():
    def handler(request):
        assert dict(request.url.params) == {
            "incident_number": "TICKET-000001",
            "breached": "false",
            "sla_definition": "first_response",
            "page": "1",
            "page_size": "25",
        }
        return httpx.Response(200, json={"items": [], "page": 1, "page_size": 25, "total": 0})

    await _client(handler).list_sla_records(
        incident_number="TICKET-000001",
        breached=False,
        sla_definition="first_response",
        page=1,
        page_size=25,
    )


@pytest.mark.anyio
async def test_list_sla_records_invalid_sla_definition_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(
            422,
            json={
                "message": "sla_definition must be one of: first_response, resolution",
                "code": "VALIDATION_ERROR",
            },
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).list_sla_records(sla_definition="bogus")
    assert exc_info.value.status_code == 422
    assert "first_response, resolution" in exc_info.value.message


@pytest.mark.anyio
async def test_list_escalations_unreachable_api_raises_upstream_unreachable_error():
    def handler(request):
        raise httpx.ConnectError("Connection refused", request=request)

    with pytest.raises(UpstreamUnreachableError):
        await _client(handler).list_escalations()


@pytest.mark.anyio
async def test_list_sla_records_5xx_raises_upstream_error_with_body_verbatim():
    def handler(request):
        return httpx.Response(500, json={"message": "internal error", "code": "INTERNAL_ERROR"})

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).list_sla_records()
    assert exc_info.value.status_code == 500
    assert exc_info.value.message == "internal error"


@pytest.mark.anyio
async def test_list_work_notes_returns_api_response_unmodified():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/incidents/INC0010001/work_notes"
        return httpx.Response(
            200,
            json=[{
                "sys_id": "INTERACTION-0000001", "incident_number": "INC0010001",
                "created_by": "customer", "note_type": "comment", "body": "Still broken",
                "created_at": "2026-09-05 00:00:00",
            }],
        )

    result = await _client(handler).list_work_notes("INC0010001")
    assert result[0]["sys_id"] == "INTERACTION-0000001"


@pytest.mark.anyio
async def test_list_work_notes_passes_pagination_params_as_query():
    def handler(request):
        assert request.url.params["page"] == "2"
        assert request.url.params["page_size"] == "50"
        return httpx.Response(200, json=[])

    await _client(handler).list_work_notes("INC0010001", page=2, page_size=50)


@pytest.mark.anyio
async def test_list_work_notes_unknown_incident_number_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(
            404, json={"message": "Incident INC9999999 not found", "code": "INCIDENT_NOT_FOUND"}
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).list_work_notes("INC9999999")
    assert exc_info.value.status_code == 404
    assert exc_info.value.message == "Incident INC9999999 not found"


@pytest.mark.anyio
async def test_add_work_note_returns_created_work_note_with_sys_id():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/incidents/INC0010001/work_notes"
        import json as _json
        body = _json.loads(request.content)
        assert body == {
            "created_by": "assist", "note_type": "comment", "body": "Auto-triaged",
        }
        return httpx.Response(
            201,
            json={
                "sys_id": "INTERACTION-0000002", "incident_number": "INC0010001",
                "created_by": "assist", "note_type": "comment", "body": "Auto-triaged",
                "created_at": "2026-09-05 00:00:01",
            },
        )

    result = await _client(handler).add_work_note("INC0010001", "assist", "comment", "Auto-triaged")
    assert result["sys_id"] == "INTERACTION-0000002"
    assert result["created_by"] == "assist"


@pytest.mark.anyio
async def test_add_work_note_unknown_incident_number_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(
            404, json={"message": "Incident INC9999999 not found", "code": "INCIDENT_NOT_FOUND"}
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).add_work_note("INC9999999", "assist", "comment", "x")
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_add_work_note_invalid_note_type_raises_upstream_error_for_422():
    def handler(request):
        return httpx.Response(
            422,
            json={
                "message": "note_type must be one of: comment, work_note, state_change, "
                           "proposal_sent",
                "code": "VALIDATION_ERROR",
            },
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).add_work_note("INC0010001", "assist", "bogus", "x")
    assert exc_info.value.status_code == 422


@pytest.mark.anyio
async def test_request_maps_connection_failure_to_unreachable_error():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(UpstreamUnreachableError):
        await _client(handler).list_work_notes("INC0010001")


@pytest.mark.anyio
async def test_request_maps_5xx_to_upstream_error():
    def handler(request):
        return httpx.Response(500, json={"message": "Internal Server Error", "code": "INTERNAL"})

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).list_work_notes("INC0010001")
    assert exc_info.value.status_code == 500


@pytest.mark.anyio
async def test_list_users_returns_api_response_unmodified():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/users"
        return httpx.Response(
            200,
            json={
                "items": [{"name": "Rui Bastos", "role": "Support Manager", "assignment_group": None}],
                "page": 1,
                "page_size": 20,
                "total": 1,
            },
        )

    result = await _client(handler).list_users()
    assert result["items"][0]["name"] == "Rui Bastos"


@pytest.mark.anyio
async def test_list_users_5xx_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(500, json={"message": "internal error", "code": "INTERNAL_ERROR"})

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).list_users()
    assert exc_info.value.status_code == 500
    assert exc_info.value.message == "internal error"


@pytest.mark.anyio
async def test_list_users_unreachable_api_raises_upstream_unreachable_error():
    def handler(request):
        raise httpx.ConnectError("Connection refused", request=request)

    with pytest.raises(UpstreamUnreachableError):
        await _client(handler).list_users()
