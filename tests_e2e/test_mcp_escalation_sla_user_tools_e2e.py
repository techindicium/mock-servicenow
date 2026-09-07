import httpx
import pytest

from tests_e2e.mcp_client import connect

# fixture-seeding.spec.md seeds only 5 Escalations and 11 SysUsers, so the default page_size
# (50) already returns the full set for both — no explicit page_size needed there.
#
# TaskSla is a different story: fixture-seeding.spec.md seeds ~2,600 records. A direct empirical
# check found that pulling the full set through the real MCP protocol in one call (page_size
# 5000) makes the streamable-http response large enough that the mcp SDK's own transport drops
# the stream ("SSE stream ended without a response") before the client ever sees a
# CallToolResult — reproduced independently of this suite's own code (a raw ClientSession
# against a hand-started mcp-server exhibits the same failure). page_size 200 is comfortably
# below whatever threshold that is, so this test compares one bounded page (same page/page_size
# on both the mcp tool call and the direct HTTP call) rather than the full ~2,600-row set —
# still a genuine same-data cross-verification, just not an all-rows-in-one-response one.
_SLA_PAGE_SIZE = 200


@pytest.mark.anyio
async def test_escalations_sla_and_users_match_real_http_state(mcp_dual_server):
    api_base_url, mcp_base_url = mcp_dual_server

    with httpx.Client(base_url=api_base_url, timeout=5) as http_client:
        http_escalations = http_client.get("/escalations").json()["items"]
        http_sla_page = http_client.get(
            "/sla", params={"page": 1, "page_size": _SLA_PAGE_SIZE}
        ).json()["items"]
        http_sla_breached = http_client.get(
            "/sla", params={"breached": "true", "page_size": 50}
        ).json()["items"]
        http_users = http_client.get("/users").json()["items"]

    async with connect(mcp_base_url) as session:
        mcp_escalations = await session.call_tool("list_escalations", {})
        mcp_sla_page = await session.call_tool(
            "list_sla_records", {"page": 1, "page_size": _SLA_PAGE_SIZE}
        )
        mcp_sla_breached = await session.call_tool(
            "list_sla_records", {"breached": True, "page_size": 50}
        )
        mcp_users = await session.call_tool("list_users", {})

    assert mcp_escalations.is_error is False
    assert mcp_sla_page.is_error is False
    assert mcp_sla_breached.is_error is False
    assert mcp_users.is_error is False

    escalation_numbers = {e["number"] for e in mcp_escalations.structured_content["items"]}
    assert escalation_numbers == {e["number"] for e in http_escalations}
    assert any(e["owner"] is None for e in mcp_escalations.structured_content["items"]), (
        "the two ownerless escalations must pass through unfiltered"
    )

    sla_page_ids = {s["sys_id"] for s in mcp_sla_page.structured_content["items"]}
    assert sla_page_ids == {s["sys_id"] for s in http_sla_page}

    breached_ids = {s["sys_id"] for s in mcp_sla_breached.structured_content["items"]}
    assert breached_ids == {s["sys_id"] for s in http_sla_breached}
    assert breached_ids, "there must be at least one breached task_sla record in the fixture"
    assert all(s["has_breached"] is True for s in mcp_sla_breached.structured_content["items"]), (
        "breached task_sla records must pass through unfiltered, with has_breached intact"
    )

    assert {u["name"] for u in mcp_users.structured_content["items"]} == {
        u["name"] for u in http_users
    }
