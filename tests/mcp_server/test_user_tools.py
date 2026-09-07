import pytest
from mcp import Client

import mcp_server.tools.users as users_tools
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp

_DEFAULT_PAGE = {"items": [], "page": 1, "page_size": 20, "total": 0}


class _FakeClient:
    """Stands in for ItsmApiClient — Task 1 already covers the real HTTP wiring."""

    def __init__(self, payload=None, error=None):
        self._payload = payload if payload is not None else _DEFAULT_PAGE
        self._error = error

    async def list_users(self):
        if self._error is not None:
            raise self._error
        return self._payload

    async def aclose(self):
        pass


@pytest.mark.anyio
async def test_list_users_tool_returns_api_result_unmodified(monkeypatch):
    payload = {
        "items": [{"name": "Rui Bastos", "role": "Support Manager", "assignment_group": None}],
        "page": 1,
        "page_size": 20,
        "total": 1,
    }
    fake = _FakeClient(payload=payload)
    monkeypatch.setattr(users_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_users", {})

    assert result.is_error is False
    # list_users' return type is a plain dict (object-shaped, matching itsm-api's paginated-page
    # response), so structured_content is the dict itself with no {"result": ...} wrapper — see
    # this plan's Architecture note (verified against the installed mcp SDK's
    # FuncMetadata.convert_result behavior for object-shaped return types).
    assert result.structured_content == payload


@pytest.mark.anyio
async def test_list_users_tool_rejects_any_input_before_http_request(monkeypatch):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeClient()

    monkeypatch.setattr(users_tools, "_client", _client_spy)

    async with Client(mcp) as client:
        result = await client.call_tool("list_users", {"foo": "bar"})

    assert result.is_error is True
    assert called["value"] is False  # schema validation rejected the call before _client() ran


@pytest.mark.anyio
async def test_list_users_tool_5xx_errors_with_verbatim_message(monkeypatch):
    fake = _FakeClient(error=UpstreamError(500, "internal error"))
    monkeypatch.setattr(users_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_users", {})

    assert result.is_error is True
    assert "internal error" in result.content[0].text


@pytest.mark.anyio
async def test_list_users_tool_unreachable_api_errors_with_clear_message(monkeypatch):
    fake = _FakeClient(
        error=UpstreamUnreachableError("Could not reach itsm-api at http://itsm-api: connection refused")
    )
    monkeypatch.setattr(users_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_users", {})

    assert result.is_error is True
    assert "itsm-api" in result.content[0].text
