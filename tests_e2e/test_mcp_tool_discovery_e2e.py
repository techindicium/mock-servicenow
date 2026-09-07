import pytest

from tests_e2e.mcp_client import connect

_EXPECTED_TOOL_NAMES = {
    "list_incidents", "get_incident", "create_incident", "update_incident",
    "list_work_notes", "add_work_note",
    "list_escalations", "list_sla_records",
    "list_users",
}


@pytest.mark.anyio
async def test_real_client_discovers_all_nine_tools_with_correct_schemas(mcp_dual_server):
    _, mcp_base_url = mcp_dual_server

    async with connect(mcp_base_url) as session:
        result = await session.list_tools()

    names = {tool.name for tool in result.tools}
    assert names == _EXPECTED_TOOL_NAMES

    by_name = {tool.name: tool for tool in result.tools}
    assert set(by_name["get_incident"].input_schema["required"]) == {"number"}
    assert set(by_name["create_incident"].input_schema["required"]) == {
        "account_id", "category", "short_description", "description", "state", "priority",
    }
    assert "number" in by_name["update_incident"].input_schema["required"]
    assert set(by_name["add_work_note"].input_schema["required"]) == {
        "incident_number", "created_by", "note_type", "body",
    }
    assert set(by_name["list_work_notes"].input_schema["required"]) == {"incident_number"}
    assert by_name["list_incidents"].input_schema.get("required", []) == []
    assert by_name["list_escalations"].input_schema.get("required", []) == []
    assert by_name["list_sla_records"].input_schema.get("required", []) == []
    assert by_name["list_users"].input_schema.get("properties", {}) == {}
