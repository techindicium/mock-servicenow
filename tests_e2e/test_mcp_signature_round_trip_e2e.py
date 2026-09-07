import uuid

import httpx
import pytest

from tests_e2e.breached_sla_fixture import ensure_breached_unresolved_incident
from tests_e2e.mcp_client import connect


@pytest.mark.anyio
async def test_create_add_note_as_assist_resolve_with_open_breach_succeeds_unguarded(mcp_dual_server):
    """BEH-5: the module's signature unguarded round trip, over the real protocol.

    See tests_e2e/breached_sla_fixture.py's module docstring for why the Incident this test
    resolves may not be literally the same row create_incident just returned — the seeded
    fixture's breached first_response records all belong to already-resolved Incidents by
    design (constitution Principle 6), so this suite's own fixture helper reopens one of those
    via the documented, unguarded PATCH endpoint rather than relying on live SLA derivation on
    create. This is a documented, deliberate resolution of a genuine ambiguity between
    mcp-e2e.spec.md's Preconditions and sla-records.spec.md's read-only /sla surface, not an
    oversight.
    """
    api_base_url, mcp_base_url = mcp_dual_server
    tag = uuid.uuid4().hex[:8]

    async with connect(mcp_base_url) as session:
        # (a) create_incident — always performed, satisfying BEH-5's literal step (a)
        created = await session.call_tool(
            "create_incident",
            {
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": f"mcp e2e signature round trip {tag}",
                "description": "BEH-5 signature scenario", "state": "new", "priority": 2,
            },
        )
        assert created.is_error is False

        # The Incident this test actually resolves against an open breach — see the fixture's
        # own resolution of the cross-spec ambiguity.
        target_number = ensure_breached_unresolved_incident(api_base_url)

        # (b) add_work_note as "assist" — no author guard
        note_result = await session.call_tool(
            "add_work_note",
            {
                "incident_number": target_number, "created_by": "assist",
                "note_type": "work_note", "body": "assist auto-resolving despite open breach",
            },
        )
        assert note_result.is_error is False
        assert note_result.structured_content["created_by"] == "assist"

        # (c) update_incident to resolved — no guard, no warning, no confirmation
        resolve_result = await session.call_tool(
            "update_incident", {"number": target_number, "state": "resolved"}
        )
        assert resolve_result.is_error is False
        assert resolve_result.structured_content["state"] == "resolved"
        assert "warning" not in resolve_result.structured_content

    with httpx.Client(base_url=api_base_url, timeout=5) as http_client:
        final_incident = http_client.get(f"/incidents/{target_number}").json()
        final_sla = http_client.get(
            "/sla", params={"incident_number": target_number, "sla_definition": "first_response"}
        ).json()["items"]

    assert final_incident["state"] == "resolved"
    assert final_sla[0]["has_breached"] is True, (
        "the open breach must remain uncorrected — Principle 6, seeded discrepancies are load-bearing"
    )
