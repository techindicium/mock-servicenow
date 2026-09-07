import pytest
from mcp import Client

import mcp_server.tools.escalations as escalations_tools
import mcp_server.tools.sla as sla_tools
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


class _FakeClient:
    """Stands in for ItsmApiClient — test_client.py already covers the real HTTP wiring.

    Escalation/SLA payloads mirror the real client's return shape: response.json() verbatim,
    i.e. the paginated {"items": [...], "page", "page_size", "total"} envelope
    app/routers/escalations.py and app/routers/sla.py actually return.
    """

    def __init__(self, escalations=None, sla_records=None, error=None):
        self._escalations = escalations if escalations is not None else {"items": []}
        self._sla_records = sla_records if sla_records is not None else {"items": []}
        self._error = error
        self.last_escalation_call = None
        self.last_sla_call = None

    async def list_escalations(self, account_id=None, open_only=None, page=None, page_size=None):
        self.last_escalation_call = dict(
            account_id=account_id, open_only=open_only, page=page, page_size=page_size
        )
        if self._error is not None:
            raise self._error
        return self._escalations

    async def list_sla_records(
        self, incident_number=None, breached=None, sla_definition=None, page=None, page_size=None
    ):
        self.last_sla_call = dict(
            incident_number=incident_number,
            breached=breached,
            sla_definition=sla_definition,
            page=page,
            page_size=page_size,
        )
        if self._error is not None:
            raise self._error
        return self._sla_records

    async def aclose(self):
        pass


@pytest.mark.anyio
async def test_list_escalations_tool_no_args_returns_full_result_including_ownerless(monkeypatch):
    fake = _FakeClient(
        escalations={
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
        }
    )
    monkeypatch.setattr(escalations_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_escalations", {})

    assert result.is_error is False
    assert fake.last_escalation_call == dict(
        account_id=None, open_only=None, page=None, page_size=None
    )
    assert result.structured_content == fake._escalations
    assert result.structured_content["items"][0]["owner"] is None


@pytest.mark.anyio
async def test_list_escalations_tool_forwards_account_id_open_only_and_pagination(monkeypatch):
    fake = _FakeClient(escalations={"items": []})
    monkeypatch.setattr(escalations_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        await client.call_tool(
            "list_escalations",
            {"account_id": "ACCOUNT-1001", "open_only": True, "page": 2, "page_size": 50},
        )

    assert fake.last_escalation_call == dict(
        account_id="ACCOUNT-1001", open_only=True, page=2, page_size=50
    )


@pytest.mark.anyio
async def test_list_sla_records_tool_no_args_returns_full_result_including_breached(monkeypatch):
    fake = _FakeClient(
        sla_records={
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
        }
    )
    monkeypatch.setattr(sla_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_sla_records", {})

    assert result.is_error is False
    assert fake.last_sla_call == dict(
        incident_number=None, breached=None, sla_definition=None, page=None, page_size=None
    )
    assert result.structured_content == fake._sla_records
    assert result.structured_content["items"][0]["has_breached"] is True


@pytest.mark.anyio
async def test_list_sla_records_tool_forwards_all_filters_and_pagination(monkeypatch):
    fake = _FakeClient(sla_records={"items": []})
    monkeypatch.setattr(sla_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        await client.call_tool(
            "list_sla_records",
            {
                "incident_number": "TICKET-000001",
                "breached": False,
                "sla_definition": "first_response",
                "page": 1,
                "page_size": 25,
            },
        )

    assert fake.last_sla_call == dict(
        incident_number="TICKET-000001",
        breached=False,
        sla_definition="first_response",
        page=1,
        page_size=25,
    )


@pytest.mark.anyio
async def test_list_escalations_tool_non_boolean_open_only_errors_before_http_call(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(escalations_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_escalations", {"open_only": "not-a-bool"})

    assert result.is_error is True
    assert fake.last_escalation_call is None  # schema validation rejected the call before _client() ran


@pytest.mark.anyio
async def test_list_sla_records_tool_non_boolean_breached_errors_before_http_call(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(sla_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_sla_records", {"breached": "not-a-bool"})

    assert result.is_error is True
    assert fake.last_sla_call is None


_UNREACHABLE_MESSAGE = "Could not reach itsm-api at http://itsm-api: connection refused"


@pytest.mark.anyio
async def test_list_escalations_tool_unreachable_api_errors_with_clear_message(monkeypatch):
    fake = _FakeClient(error=UpstreamUnreachableError(_UNREACHABLE_MESSAGE))
    monkeypatch.setattr(escalations_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_escalations", {})

    assert result.is_error is True
    assert "itsm-api" in result.content[0].text


@pytest.mark.anyio
async def test_list_sla_records_tool_5xx_errors_with_body_verbatim(monkeypatch):
    fake = _FakeClient(error=UpstreamError(500, "internal error"))
    monkeypatch.setattr(sla_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_sla_records", {})

    assert result.is_error is True
    assert "internal error" in result.content[0].text


@pytest.mark.anyio
async def test_list_sla_records_tool_invalid_sla_definition_errors_with_422_message_verbatim(
    monkeypatch,
):
    fake = _FakeClient(
        error=UpstreamError(422, "sla_definition must be one of: first_response, resolution")
    )
    monkeypatch.setattr(sla_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        # Note: "bogus" is a syntactically valid str, so this reaches the (faked) HTTP call rather
        # than failing schema validation — see SA-2 in the plan header.
        result = await client.call_tool("list_sla_records", {"sla_definition": "bogus"})

    assert result.is_error is True
    assert "first_response, resolution" in result.content[0].text
