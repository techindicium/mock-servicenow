import pytest
from mcp import Client

import mcp_server.tools.escalations as escalations_tools
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
