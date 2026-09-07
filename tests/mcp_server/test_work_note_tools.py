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
        return {"items": self._notes, "page": 1, "page_size": 50, "total": len(self._notes)}

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
    assert result.structured_content == {
        "items": [_SAMPLE_NOTE], "page": 1, "page_size": 50, "total": 1,
    }


@pytest.mark.anyio
async def test_list_work_notes_tool_passes_pagination_params(monkeypatch):
    captured = {}

    class _CapturingClient(_FakeClient):
        async def list_work_notes(self, incident_number, page=None, page_size=None):
            captured["page"] = page
            captured["page_size"] = page_size
            return {"items": [], "page": page or 1, "page_size": page_size or 50, "total": 0}

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


@pytest.mark.anyio
@pytest.mark.parametrize("author", ["customer", "jane.agent", "assist"])
async def test_add_work_note_tool_succeeds_unconditionally_for_any_created_by(monkeypatch, author):
    created = {**_CREATED_NOTE, "created_by": author}
    fake = _FakeAddClient(created=created)
    monkeypatch.setattr(work_notes_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "add_work_note",
            {
                "incident_number": "INC0010001", "created_by": author,
                "note_type": "comment", "body": "x",
            },
        )

    assert result.is_error is False
    assert fake.received == ("INC0010001", author, "comment", "x")


@pytest.mark.anyio
async def test_add_work_note_tool_unknown_incident_number_errors_with_verbatim_message(monkeypatch):
    fake = _FakeAddClient(error=UpstreamError(404, "Incident INC9999999 not found"))
    monkeypatch.setattr(work_notes_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "add_work_note",
            {
                "incident_number": "INC9999999", "created_by": "assist",
                "note_type": "comment", "body": "x",
            },
        )

    assert result.is_error is True
    assert "Incident INC9999999 not found" in result.content[0].text


@pytest.mark.anyio
async def test_add_work_note_tool_invalid_note_type_errors_with_verbatim_message(monkeypatch):
    fake = _FakeAddClient(
        error=UpstreamError(
            422,
            "note_type must be one of: comment, work_note, state_change, proposal_sent",
        )
    )
    monkeypatch.setattr(work_notes_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "add_work_note",
            {
                "incident_number": "INC0010001", "created_by": "assist",
                "note_type": "bogus", "body": "x",
            },
        )

    assert result.is_error is True
    assert "note_type must be one of" in result.content[0].text


_UNREACHABLE_MESSAGE = "Could not reach itsm-api at http://itsm-api: connection refused"


class _UnreachableClient(_FakeClient):
    async def list_work_notes(self, incident_number, page=None, page_size=None):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)

    async def add_work_note(self, incident_number, created_by, note_type, body):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "tool_name, arguments",
    [
        ("list_work_notes", {"incident_number": "INC0010001"}),
        (
            "add_work_note",
            {
                "incident_number": "INC0010001", "created_by": "assist",
                "note_type": "comment", "body": "x",
            },
        ),
    ],
)
async def test_work_note_tool_unreachable_api_errors_with_clear_message(
    monkeypatch, tool_name, arguments
):
    monkeypatch.setattr(work_notes_tools, "_client", lambda: _UnreachableClient())

    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is True
    assert "itsm-api" in result.content[0].text


class _FiveHundredClient(_FakeClient):
    async def list_work_notes(self, incident_number, page=None, page_size=None):
        raise UpstreamError(500, "Internal Server Error")

    async def add_work_note(self, incident_number, created_by, note_type, body):
        raise UpstreamError(500, "Internal Server Error")


@pytest.mark.anyio
@pytest.mark.parametrize(
    "tool_name, arguments",
    [
        ("list_work_notes", {"incident_number": "INC0010001"}),
        (
            "add_work_note",
            {
                "incident_number": "INC0010001", "created_by": "assist",
                "note_type": "comment", "body": "x",
            },
        ),
    ],
)
async def test_work_note_tool_5xx_errors_with_verbatim_message(monkeypatch, tool_name, arguments):
    monkeypatch.setattr(work_notes_tools, "_client", lambda: _FiveHundredClient())

    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is True
    assert "Internal Server Error" in result.content[0].text
