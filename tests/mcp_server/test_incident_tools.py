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


class _FakeCreateClient(_FakeClient):
    def __init__(self, created=None, error=None):
        super().__init__()
        self._created = created
        self._error = error

    async def create_incident(self, **kwargs):
        if self._error is not None:
            raise self._error
        return self._created


@pytest.mark.anyio
async def test_create_incident_tool_requires_all_six_fields_and_returns_created_incident(monkeypatch):
    monkeypatch.setattr(
        incidents_tools, "_client", lambda: _FakeCreateClient(created=_SAMPLE_INCIDENT)
    )

    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_incident",
            {
                "account_id": "ACCOUNT-1001", "category": "billing",
                "short_description": "Invoice mismatch",
                "description": "Customer reports a mismatch.",
                "state": "new", "priority": 2,
            },
        )

    assert result.is_error is False
    assert result.structured_content == _SAMPLE_INCIDENT


@pytest.mark.anyio
@pytest.mark.parametrize("missing_field", [
    "account_id", "category", "short_description", "description", "state", "priority",
])
async def test_create_incident_tool_missing_any_required_field_errors_before_http_request(
    monkeypatch, missing_field
):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeCreateClient()

    monkeypatch.setattr(incidents_tools, "_client", _client_spy)

    full_args = {
        "account_id": "ACCOUNT-1001", "category": "billing",
        "short_description": "Invoice mismatch", "description": "Customer reports a mismatch.",
        "state": "new", "priority": 2,
    }
    args = {k: v for k, v in full_args.items() if k != missing_field}

    async with Client(mcp) as client:
        result = await client.call_tool("create_incident", args)

    assert result.is_error is True
    assert called["value"] is False  # schema validation rejected the call before _client() ran


@pytest.mark.anyio
async def test_create_incident_tool_invalid_category_errors_with_verbatim_message(monkeypatch):
    fake = _FakeCreateClient(
        error=UpstreamError(
            422,
            "category must be one of: account-opening, payments, cards, "
            "scheduled-payments, fees, statements, access, account-restrictions",
        )
    )
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_incident",
            {
                "account_id": "ACCOUNT-1001", "category": "not-a-real-category",
                "short_description": "x", "description": "y", "state": "new", "priority": 2,
            },
        )

    assert result.is_error is True
    assert "category must be one of" in result.content[0].text


class _FakeUpdateClient(_FakeClient):
    def __init__(self, updated=None, error=None):
        super().__init__()
        self._updated = updated
        self._error = error
        self.received_kwargs = None

    async def update_incident(self, number, **fields):
        self.received_kwargs = fields
        if self._error is not None:
            raise self._error
        return self._updated


@pytest.mark.anyio
async def test_update_incident_tool_updates_mutable_fields_and_returns_result(monkeypatch):
    updated = {**_SAMPLE_INCIDENT, "assigned_to": "Priya N."}
    fake = _FakeUpdateClient(updated=updated)
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "update_incident", {"number": "TICKET-004417", "assigned_to": "Priya N."}
        )

    assert result.is_error is False
    assert result.structured_content == updated
    assert fake.received_kwargs == {
        "state": None, "priority": None, "assigned_to": "Priya N.", "assignment_group": None,
    }


@pytest.mark.anyio
async def test_update_incident_tool_resolves_an_incident_with_an_open_sla_breach_unconditionally(
    monkeypatch
):
    """BEH-6 / Non-Negotiable Principle 5: this is the explicit 'confirm no guard exists' test
    from the Actionable Task Map. The Incident being resolved here carries a first_response
    TaskSla with has_breached: true and no customer-facing work note — exactly the seeded
    discrepancy #3 scenario (see incident-lifecycle.spec.md System Constitution Reference,
    Principle 6). The tool must return success with no refusal, no injected warning field, and
    no confirmation step, proving the tool layer never inspects task_sla state before calling
    itsm-api."""
    breached_incident_after_resolve = {
        **_SAMPLE_INCIDENT,
        "number": "TICKET-004480",
        "state": "resolved",
        "resolved_at": "2026-09-07T12:00:00Z",
        # Included only to document the scenario for the reader; update_incident's own response
        # shape is whatever itsm-api returns for the Incident resource — task_sla is a separate
        # entity (sla-records spec) this tool never fetches or reasons about.
    }
    fake = _FakeUpdateClient(updated=breached_incident_after_resolve)
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "update_incident", {"number": "TICKET-004480", "state": "resolved"}
        )

    # No refusal, no injected warning field, no confirmation step: the call succeeds exactly like
    # any other update, and the tool's return value is exactly what itsm-api sent back — nothing
    # added, nothing withheld.
    assert result.is_error is False
    assert result.structured_content == breached_incident_after_resolve
    assert "warning" not in result.structured_content
    assert "confirm" not in result.structured_content
    assert fake.received_kwargs["state"] == "resolved"


@pytest.mark.anyio
async def test_update_incident_tool_ignores_number_in_the_patch_body(monkeypatch):
    fake = _FakeUpdateClient(updated=_SAMPLE_INCIDENT)
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        await client.call_tool(
            "update_incident", {"number": "TICKET-004417", "state": "resolved"}
        )

    # "number" is used only to select which Incident to PATCH — it is structurally impossible
    # for it to also appear as a mutable field kwarg, satisfying the Preconditions clause.
    assert "number" not in fake.received_kwargs


@pytest.mark.anyio
async def test_update_incident_tool_unknown_number_errors_with_verbatim_message(monkeypatch):
    fake = _FakeUpdateClient(error=UpstreamError(404, "Incident TICKET-999999 not found"))
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("update_incident", {"number": "TICKET-999999", "state": "resolved"})

    assert result.is_error is True
    assert "Incident TICKET-999999 not found" in result.content[0].text


@pytest.mark.anyio
async def test_update_incident_tool_invalid_state_errors_with_verbatim_message(monkeypatch):
    fake = _FakeUpdateClient(
        error=UpstreamError(422, "state must be one of: new, in_progress, on_hold, resolved, closed")
    )
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "update_incident", {"number": "TICKET-004417", "state": "not-a-real-state"}
        )

    assert result.is_error is True
    assert "state must be one of" in result.content[0].text


@pytest.mark.anyio
async def test_update_incident_tool_missing_number_errors_before_http_request(monkeypatch):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeUpdateClient()

    monkeypatch.setattr(incidents_tools, "_client", _client_spy)

    async with Client(mcp) as client:
        result = await client.call_tool("update_incident", {"state": "resolved"})  # missing "number"

    assert result.is_error is True
    assert called["value"] is False


_UNREACHABLE_MESSAGE = "Could not reach itsm-api at http://itsm-api: connection refused"


class _UnreachableClient(_FakeClient):
    async def list_incidents(self, **kwargs):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)

    async def get_incident(self, number):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)

    async def create_incident(self, **kwargs):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)

    async def update_incident(self, number, **fields):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)


class _FiveHundredClient(_FakeClient):
    async def list_incidents(self, **kwargs):
        raise UpstreamError(500, "Internal Server Error")

    async def get_incident(self, number):
        raise UpstreamError(500, "Internal Server Error")

    async def create_incident(self, **kwargs):
        raise UpstreamError(500, "Internal Server Error")

    async def update_incident(self, number, **fields):
        raise UpstreamError(500, "Internal Server Error")


_ALL_TOOL_CALLS = [
    ("list_incidents", {}),
    ("get_incident", {"number": "TICKET-004417"}),
    (
        "create_incident",
        {
            "account_id": "ACCOUNT-1001", "category": "billing", "short_description": "x",
            "description": "y", "state": "new", "priority": 2,
        },
    ),
    ("update_incident", {"number": "TICKET-004417", "state": "resolved"}),
]


@pytest.mark.anyio
@pytest.mark.parametrize("tool_name, arguments", _ALL_TOOL_CALLS)
async def test_incident_tool_unreachable_api_errors_with_clear_message(
    monkeypatch, tool_name, arguments
):
    monkeypatch.setattr(incidents_tools, "_client", lambda: _UnreachableClient())

    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is True
    assert "itsm-api" in result.content[0].text


@pytest.mark.anyio
@pytest.mark.parametrize("tool_name, arguments", _ALL_TOOL_CALLS)
async def test_incident_tool_5xx_errors_with_verbatim_message(monkeypatch, tool_name, arguments):
    monkeypatch.setattr(incidents_tools, "_client", lambda: _FiveHundredClient())

    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is True
    assert "Internal Server Error" in result.content[0].text
