import pytest
from mcp import Client

import mcp_server.tools.incidents as incidents_tools
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


class _FakeClient:
    """Stands in for ItsmApiClient — Tasks 1/2 already cover the real HTTP wiring."""

    def __init__(self, incidents=None, incident=None):
        self._incidents = incidents if incidents is not None else {"items": []}
        self._incident = incident

    async def list_incidents(self, **kwargs):
        return self._incidents

    async def get_incident(self, number):
        return self._incident

    async def aclose(self):
        pass


_SAMPLE_INCIDENT = {
    "number": "TICKET-004417", "account_id": "ACCOUNT-1001", "category": "billing",
    "short_description": "Invoice mismatch", "description": "Customer reports a mismatch.",
    "state": "new", "priority": 2, "opened_at": "2026-09-01T00:00:00Z", "resolved_at": None,
    "assigned_to": None, "assignment_group": "Support Tier 1", "escalated": False,
}


@pytest.mark.anyio
async def test_list_incidents_tool_returns_api_result_unmodified(monkeypatch):
    fake = _FakeClient(incidents={"items": [_SAMPLE_INCIDENT], "page": 1})
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_incidents", {})

    assert result.is_error is False
    assert result.structured_content == {"items": [_SAMPLE_INCIDENT], "page": 1}


@pytest.mark.anyio
async def test_get_incident_tool_returns_the_incident(monkeypatch):
    monkeypatch.setattr(incidents_tools, "_client", lambda: _FakeClient(incident=_SAMPLE_INCIDENT))

    async with Client(mcp) as client:
        result = await client.call_tool("get_incident", {"number": "TICKET-004417"})

    assert result.is_error is False
    assert result.structured_content == _SAMPLE_INCIDENT


class _NotFoundGetClient(_FakeClient):
    async def get_incident(self, number):
        raise UpstreamError(404, "Incident TICKET-999999 not found")


@pytest.mark.anyio
async def test_get_incident_tool_unknown_number_errors_with_verbatim_message(monkeypatch):
    monkeypatch.setattr(incidents_tools, "_client", lambda: _NotFoundGetClient())

    async with Client(mcp) as client:
        result = await client.call_tool("get_incident", {"number": "TICKET-999999"})

    assert result.is_error is True
    assert "Incident TICKET-999999 not found" in result.content[0].text


@pytest.mark.anyio
async def test_get_incident_tool_missing_number_errors_before_http_request(monkeypatch):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeClient()

    monkeypatch.setattr(incidents_tools, "_client", _client_spy)

    async with Client(mcp) as client:
        result = await client.call_tool("get_incident", {})  # missing required "number"

    assert result.is_error is True
    assert called["value"] is False  # schema validation rejected the call before _client() ran


@pytest.mark.anyio
async def test_list_incidents_tool_invalid_priority_type_errors_before_http_request(monkeypatch):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeClient()

    monkeypatch.setattr(incidents_tools, "_client", _client_spy)

    async with Client(mcp) as client:
        # "escalated" is declared bool; a non-boolean string fails schema validation.
        result = await client.call_tool("list_incidents", {"escalated": "not-a-bool"})

    assert result.is_error is True
    assert called["value"] is False
