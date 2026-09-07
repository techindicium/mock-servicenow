import uuid

import httpx
import pytest

from tests_e2e.mcp_client import connect


@pytest.mark.anyio
async def test_add_work_note_matches_real_http_state(mcp_dual_server):
    api_base_url, mcp_base_url = mcp_dual_server
    tag = uuid.uuid4().hex[:8]

    async with connect(mcp_base_url) as session:
        created = await session.call_tool(
            "create_incident",
            {
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": f"mcp e2e work note incident {tag}",
                "description": "for work-note e2e", "state": "new", "priority": 3,
            },
        )
        assert created.is_error is False
        number = created.structured_content["number"]

        note_result = await session.call_tool(
            "add_work_note",
            {
                "incident_number": number, "created_by": "assist",
                "note_type": "work_note", "body": "e2e note",
            },
        )
        assert note_result.is_error is False
        assert note_result.structured_content["created_by"] == "assist"  # BEH-4: no author guard
        sys_id = note_result.structured_content["sys_id"]

    with httpx.Client(base_url=api_base_url, timeout=5) as http_client:
        http_notes = http_client.get(f"/incidents/{number}/work_notes").json()["items"]
        assert any(n["sys_id"] == sys_id and n["created_by"] == "assist" for n in http_notes)


@pytest.mark.anyio
@pytest.mark.xfail(
    reason=(
        "Genuine bug in the existing (not-to-be-modified) mcp_server/tools/work_notes.py: "
        "list_work_notes is annotated `-> list[dict]`, but itsm-api's real GET "
        ".../work_notes response is a paginated dict ({'items': [...], 'page': ..., "
        "'page_size': ..., 'total': ...}), not a bare list. The mcp SDK validates the tool's "
        "return value against its declared output type before it ever reaches the client, so "
        "every real call to list_work_notes raises a pydantic ValidationError inside "
        "mcp/server/mcpserver/tools/base.py::Tool.run, which the SDK reports to the client as "
        "a generic CallToolResult(isError=True, content=[TextContent(text='Error executing "
        "tool list_work_notes')]) — confirmed by direct reproduction against the real "
        "streamable-http transport. This is a production defect in mcp_server, out of scope "
        "for this test-only suite to fix (see mcp-e2e's own constraints); tracked here as a "
        "strict xfail so it surfaces loudly (XPASS) the moment mcp_server's return annotation "
        "is corrected upstream."
    ),
    strict=True,
)
async def test_list_work_notes_over_real_mcp_protocol(mcp_dual_server):
    _, mcp_base_url = mcp_dual_server
    tag = uuid.uuid4().hex[:8]

    async with connect(mcp_base_url) as session:
        created = await session.call_tool(
            "create_incident",
            {
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": f"mcp e2e list work notes incident {tag}",
                "description": "for work-note e2e", "state": "new", "priority": 3,
            },
        )
        number = created.structured_content["number"]

        note_result = await session.call_tool(
            "add_work_note",
            {
                "incident_number": number, "created_by": "assist",
                "note_type": "work_note", "body": "e2e note for list assertion",
            },
        )
        sys_id = note_result.structured_content["sys_id"]

        listed = await session.call_tool("list_work_notes", {"incident_number": number})
        assert listed.is_error is False
        notes = listed.structured_content["items"]
        assert any(n["sys_id"] == sys_id for n in notes)
