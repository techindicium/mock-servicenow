import pytest

from tests_e2e.mcp_client import connect


@pytest.mark.anyio
async def test_schema_invalid_tool_input_surfaces_as_call_tool_result_error(mcp_dual_server):  # BEH-6
    _, mcp_base_url = mcp_dual_server

    async with connect(mcp_base_url) as session:
        result = await session.call_tool("get_incident", {})  # missing required "number"

    assert result.is_error is True
    assert result.content  # a message is present for the model to see
    # The session itself stays open — no raised transport-level exception, per BEH-6's revision-2 fix.
    async with connect(mcp_base_url) as session2:
        alive = await session2.list_tools()
        assert alive.tools


@pytest.mark.anyio
async def test_unreachable_upstream_surfaces_as_call_tool_result_error(mcp_server_unreachable):  # BEH-7
    async with connect(mcp_server_unreachable) as session:
        result = await session.call_tool("list_incidents", {})

    assert result.is_error is True
    assert "unreachable" in result.content[0].text.lower() or "connect" in result.content[0].text.lower()


@pytest.mark.skip(
    reason=(
        "BEH-8 needs a real, reliably-reproducible upstream 5xx from itsm-api over real HTTP "
        "(never mocked/simulated, per this spec's own Preconditions). None of the six itsm-api "
        "specs document a request that deterministically produces a 5xx (all documented error "
        "paths are 404/422/400). This test is intentionally left as a visible, tracked skip "
        "rather than a trivially-passing assertion — see mcp-e2e.spec.md's Error Cases table and "
        "this suite's own Quality Gates residual risk #2. Un-skip and tighten the assertion below "
        "only once a concrete 5xx trigger is confirmed against itsm-api's actual implementation."
    )
)
@pytest.mark.anyio
async def test_upstream_5xx_passed_through_verbatim(mcp_dual_server):  # BEH-8
    _, mcp_base_url = mcp_dual_server

    async with connect(mcp_base_url) as session:
        # Replace this call with whichever real request itsm-api is confirmed to answer with a
        # 5xx once that trigger is known — do not remove the skip until this line is real.
        result = await session.call_tool("get_incident", {"number": "TICKET-999999999999999999999"})

    assert result.is_error is True
    assert result.content and result.content[0].text, (
        "BEH-8 requires the API's 5xx error body to pass through verbatim, not a generic or "
        "swallowed error — assert the exact body text here once the real trigger is wired in"
    )
