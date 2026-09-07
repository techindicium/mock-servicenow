import pytest
from mcp import Client

import mcp_server.tools.work_notes as work_notes_tools
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


class _FakeClient:
    """Stands in for ItsmApiClient — Task 1 already covers the real HTTP wiring."""

    def __init__(self, notes=None, created=None):
        self._notes = notes or []
        self._created = created

    async def list_work_notes(self, incident_number, page=None, page_size=None):
        return self._notes

    async def add_work_note(self, incident_number, created_by, note_type, body):
        return self._created

    async def aclose(self):
        pass


_SAMPLE_NOTE = {
    "sys_id": "INTERACTION-0000001", "incident_number": "INC0010001",
    "created_by": "customer", "note_type": "comment", "body": "Still broken",
    "created_at": "2026-09-05 00:00:00",
}


@pytest.mark.anyio
async def test_list_work_notes_tool_returns_api_result_unmodified(monkeypatch):
    fake = _FakeClient(notes=[_SAMPLE_NOTE])
    monkeypatch.setattr(work_notes_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_work_notes", {"incident_number": "INC0010001"})

    assert result.is_error is False
    assert result.structured_content == {"result": [_SAMPLE_NOTE]}


@pytest.mark.anyio
async def test_list_work_notes_tool_passes_pagination_params(monkeypatch):
    captured = {}

    class _CapturingClient(_FakeClient):
        async def list_work_notes(self, incident_number, page=None, page_size=None):
            captured["page"] = page
            captured["page_size"] = page_size
            return []

    monkeypatch.setattr(work_notes_tools, "_client", lambda: _CapturingClient())

    async with Client(mcp) as client:
        await client.call_tool(
            "list_work_notes", {"incident_number": "INC0010001", "page": 2, "page_size": 50}
        )

    assert captured == {"page": 2, "page_size": 50}


class _NotFoundListClient(_FakeClient):
    async def list_work_notes(self, incident_number, page=None, page_size=None):
        raise UpstreamError(404, "Incident INC9999999 not found")


@pytest.mark.anyio
async def test_list_work_notes_tool_unknown_incident_number_errors_with_verbatim_message(monkeypatch):
    monkeypatch.setattr(work_notes_tools, "_client", lambda: _NotFoundListClient())

    async with Client(mcp) as client:
        result = await client.call_tool("list_work_notes", {"incident_number": "INC9999999"})

    assert result.is_error is True
    assert "Incident INC9999999 not found" in result.content[0].text


@pytest.mark.anyio
async def test_list_work_notes_tool_missing_incident_number_errors_before_http_request(monkeypatch):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeClient()

    monkeypatch.setattr(work_notes_tools, "_client", _client_spy)

    async with Client(mcp) as client:
        result = await client.call_tool("list_work_notes", {})  # missing required incident_number

    assert result.is_error is True
    assert called["value"] is False  # schema validation rejected the call before _client() ran


_CREATED_NOTE = {
    "sys_id": "INTERACTION-0000002", "incident_number": "INC0010001",
    "created_by": "assist", "note_type": "comment", "body": "Auto-triaged",
    "created_at": "2026-09-05 00:00:01",
}


class _FakeAddClient(_FakeClient):
    def __init__(self, created=None, error=None):
        super().__init__()
        self._created = created
        self._error = error
        self.received = None

    async def add_work_note(self, incident_number, created_by, note_type, body):
        self.received = (incident_number, created_by, note_type, body)
        if self._error is not None:
            raise self._error
        return self._created


@pytest.mark.anyio
async def test_add_work_note_tool_creates_and_returns_work_note_with_sys_id(monkeypatch):
    fake = _FakeAddClient(created=_CREATED_NOTE)
    monkeypatch.setattr(work_notes_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "add_work_note",
            {
                "incident_number": "INC0010001",
                "created_by": "assist",
                "note_type": "comment",
                "body": "Auto-triaged",
            },
        )

    assert result.is_error is False
    assert result.structured_content == _CREATED_NOTE
    assert fake.received == ("INC0010001", "assist", "comment", "Auto-triaged")


@pytest.mark.anyio
@pytest.mark.parametrize("missing_field", ["incident_number", "created_by", "note_type", "body"])
async def test_add_work_note_tool_missing_required_field_errors_before_http_request(
    monkeypatch, missing_field
):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeAddClient()

    monkeypatch.setattr(work_notes_tools, "_client", _client_spy)

    arguments = {
        "incident_number": "INC0010001", "created_by": "assist",
        "note_type": "comment", "body": "x",
    }
    del arguments[missing_field]

    async with Client(mcp) as client:
        result = await client.call_tool("add_work_note", arguments)

    assert result.is_error is True
    assert called["value"] is False  # schema validation rejected the call before _client() ran


@pytest.mark.anyio
async def test_add_work_note_tool_non_string_created_by_errors_before_http_request(monkeypatch):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeAddClient()

    monkeypatch.setattr(work_notes_tools, "_client", _client_spy)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "add_work_note",
            {
                "incident_number": "INC0010001", "created_by": 12345,  # non-string
                "note_type": "comment", "body": "x",
            },
        )

    assert result.is_error is True
    assert called["value"] is False
