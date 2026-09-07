import uuid

import httpx
import pytest

from tests_e2e.mcp_client import connect


@pytest.mark.anyio
async def test_full_incident_lifecycle_over_real_mcp_protocol_cross_verified(mcp_dual_server):
    api_base_url, mcp_base_url = mcp_dual_server
    tag = uuid.uuid4().hex[:8]

    async with connect(mcp_base_url) as session:
        created = await session.call_tool(
            "create_incident",
            {
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": f"mcp e2e incident {tag}",
                "description": "created by tests_e2e/test_mcp_incident_tools_e2e.py",
                "state": "new", "priority": 3,
            },
        )
        assert created.is_error is False
        number = created.structured_content["number"]

        with httpx.Client(base_url=api_base_url, timeout=5) as http_client:
            assert http_client.get(f"/incidents/{number}").status_code == 200

        first_page = await session.call_tool("list_incidents", {"account_id": "ACCOUNT-1001"})
        assert first_page.is_error is False
        page_size = first_page.structured_content["page_size"]
        total = first_page.structured_content["total"]
        last_page_number = -(-total // page_size)  # ceil division

        # The new Incident's server-assigned number is the current global max + 1 (see
        # app/db.py::next_incident_number), so within this account's ORDER BY number ASC
        # filtered list it sorts last — on the final page, not necessarily the first.
        last_page = await session.call_tool(
            "list_incidents", {"account_id": "ACCOUNT-1001", "page": last_page_number}
        )
        assert last_page.is_error is False
        items = last_page.structured_content["items"]
        assert any(i["number"] == number for i in items)

        fetched = await session.call_tool("get_incident", {"number": number})
        assert fetched.is_error is False
        assert fetched.structured_content["number"] == number

        updated = await session.call_tool(
            "update_incident", {"number": number, "priority": 1, "state": "in_progress"}
        )
        assert updated.is_error is False
        assert updated.structured_content["priority"] == 1
        assert updated.structured_content["state"] == "in_progress"

    with httpx.Client(base_url=api_base_url, timeout=5) as http_client:
        api_view = http_client.get(f"/incidents/{number}").json()
        assert api_view["priority"] == 1
        assert api_view["state"] == "in_progress"
