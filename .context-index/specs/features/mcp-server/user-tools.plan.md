# Implementation Plan: User MCP tool (list_users)

> **Methodology:** adev
> **Charter:** .context-index/specs/features/mcp-server/charter.md
> **Spec:** .context-index/specs/features/mcp-server/user-tools.spec.md
> **Review:** review-passed
> **Platform:** Python 3.11, no web framework in mcp-server itself (uses the `mcp` SDK's `MCPServer`), `httpx` for the upstream HTTP call

**Goal:** Add a `list_users` MCP tool to a newly-scaffolded `mcp_server` package that wraps `itsm-api`'s `GET /users` endpoint verbatim, with a strictly empty input schema that rejects any argument before an HTTP call is ever made.

**Architecture:** No `mcp_server/` package exists yet in this repo besides `PRD.md`, `README.md`,
and `.context-index/` — greenfield. Four `mcp-server` plans were authored independently against
this same greenfield package (`incident-tools`, `work-note-tools`, `escalation-and-sla-tools`,
`user-tools` [this plan]); to avoid four independent copies of the same foundation colliding,
`incident-tools.plan.md` is the designated foundation owner and this plan **extends** its output.
`incident-tools.plan.md` Task 1 creates `mcp_server/config.py`, `mcp_server/errors.py`, the base
`mcp_server/client.py` (a thin `ItsmApiClient` wrapping `httpx.AsyncClient`), `requirements.txt`,
`pytest.ini`, and the `tests/mcp_server/` scaffold. Its Task 3 creates `mcp_server/server.py` (a
module-level `MCPServer` instance and `main()`) and `mcp_server/tools/__init__.py`. This plan adds
`list_users` to the existing `ItsmApiClient` (Task 1) and registers a `@mcp.tool()`-decorated
`list_users` function in a new `mcp_server/tools/users.py` (Task 2) that maps
`UpstreamError`/`UpstreamUnreachableError` to `ToolError`, exactly mirroring `mock-jira`'s
`mcp_server/` pattern (per this repo's constitution "Patterns to Follow").

**BEH-2's dependency on `incident-tools.plan.md`'s `ArgModelBase` patch:** the installed `mcp`
SDK's auto-generated per-tool argument model (`ArgModelBase`, in
`mcp.server.mcpserver.utilities.func_metadata`) defaults to pydantic's `extra="ignore"`, so a
zero-parameter tool like `list_users` would otherwise silently drop unexpected arguments and
proceed to the real HTTP call — violating BEH-2, which requires the call to error *before* any
HTTP request is made. Rather than patching `ArgModelBase` per tool module — which would apply the
fix once per sibling plan, redundantly, since all `mcp-server` tools share one `mcp` instance —
`incident-tools.plan.md` Task 3 applies `ArgModelBase.model_config = ConfigDict(extra="forbid")`
exactly once in `mcp_server/server.py`, immediately after constructing the `MCPServer` instance
and before any tool module is imported. This plan's investigation of the installed `mcp` SDK's
source (`Tool.from_function` calls `func_arg_metadata.arg_model.model_json_schema(by_alias=True)`
with no other hook to inject `extra="forbid"` per tool) is what surfaced this fix in the first
place and is the basis `incident-tools.plan.md` Task 3 cites; this plan's own Task 2 relies on
that patch already being in place rather than reapplying it, so every subsequently-generated
argument model — starting with `list_users`'s — is strict: extra keys are rejected at validation
time, and the published JSON schema carries `additionalProperties: false`.

`list_users`'s return type is `dict[str, Any]` — itsm-api's `GET /users` returns "a paginated page" per `user-directory.spec.md` (an object, not a bare array), so the mcp SDK does not wrap the result under a `{"result": ...}` key (that wrapping only applies to non-object return types such as a bare `list`); the tool's `structured_content` is the upstream page object unmodified, matching BEH-1.

Test granularity resolves to `per-behavior` (source: manifest — `test_policy.granularity: per-behavior` in `.context-index/manifest.yaml`, no module override for `mcp-server`). All three of this spec's behaviors (BEH-1, BEH-2, BEH-3) are implemented together across Tasks 2–3 and share one suite, `tests/mcp_server/test_user_tools.py`. Task 1's client-layer test (`tests/mcp_server/test_client.py`) is a separate, lower-level suite for the HTTP wrapper itself, mirroring `mock-jira`'s own split between `test_client.py` and `test_*_tools.py`.

---

## File Structure

**Create:**
- `mcp_server/tools/users.py` — the `list_users` tool
- `tests/mcp_server/test_user_tools.py` — unit tests for the `list_users` tool (BEH-1, BEH-2, BEH-3)

**Modify:**
- `mcp_server/client.py` — add `list_users()` to the existing `ItsmApiClient` class **created by
  `incident-tools.plan.md` Task 1** — this plan never recreates the file or its `_request()` helper
- `mcp_server/server.py` — add `import mcp_server.tools.users` inside `main()` (created by
  `incident-tools.plan.md` Task 3, which also carries the `ArgModelBase` strict-schema patch this
  spec's BEH-2 depends on — this plan never recreates the `mcp` instance or reapplies the patch)
- `tests/mcp_server/test_client.py` — extend with `list_users` coverage (created by
  `incident-tools.plan.md` Task 1)

**Reference (read, do not modify):**
- `mcp_server/config.py`, `mcp_server/errors.py`, `mcp_server/client.py`, `mcp_server/server.py`,
  `mcp_server/tools/__init__.py`, `requirements.txt`, `pytest.ini`, `tests/mcp_server/__init__.py`,
  `tests/mcp_server/conftest.py` — the shared foundation created by `incident-tools.plan.md`
  Tasks 1 and 3; this plan depends on all of these existing and extends two of them (`client.py`,
  `server.py`) per the Modify list above
- `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/client.py`, `mcp_server/server.py`, `mcp_server/tools/projects.py`, `mcp_server/errors.py`, `mcp_server/config.py` — the exact pattern this plan mirrors (sibling repo, same author, explicitly named as the convention to follow in this repo's constitution)
- `/Users/dpavancini/Development/adev-course/mock-jira/tests/mcp_server/test_client.py`, `test_project_tools.py`, `test_config.py`, `conftest.py` — unit test idioms to copy (fake client via `monkeypatch.setattr`, `httpx.MockTransport`, `mcp.Client`/`call_tool`)
- `.venv`/site-packages `mcp/server/mcpserver/utilities/func_metadata.py`, `mcp/server/mcpserver/tools/base.py` (in `mock-jira`'s `.venv`, since `mock-servicenow` has no venv yet) — confirms `ArgModelBase` has no `extra="forbid"` by default and that `Tool.from_function` offers no other injection point for a strict schema; this is the investigation `incident-tools.plan.md` Task 3 cites for the patch this spec's BEH-2 relies on
- `.context-index/specs/features/itsm-api/user-directory.spec.md` — the upstream contract this tool wraps (field shapes, pagination-page response shape, no auth)

---

## Context Packets

### Task 1 Context
- Spec: `.context-index/specs/features/mcp-server/user-tools.spec.md` (Preconditions, BEH-1, BEH-3, Error Cases table)
- Charter: `.context-index/specs/features/mcp-server/charter.md` (capability: `list_users tool`; Domain Model invariants on verbatim error passthrough)
- Upstream contract: `.context-index/specs/features/itsm-api/user-directory.spec.md` (BEH-1, BEH-4 — paginated page shape; no auth)
- Source files (from `incident-tools.plan.md` Task 1, full read — extending, not replacing): `mcp_server/client.py`, `mcp_server/errors.py`, `mcp_server/config.py`
- Reference source: `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/client.py`, `mcp_server/errors.py`, `mcp_server/config.py` (full read — pattern to mirror exactly)
- Reference tests: `/Users/dpavancini/Development/adev-course/mock-jira/tests/mcp_server/test_client.py` (full read — `httpx.MockTransport` idiom)

### Task 2 Context
- Spec: `.context-index/specs/features/mcp-server/user-tools.spec.md` (BEH-2, Error Cases table)
- Task 1 (this plan) output: `mcp_server/client.py` (extended with `list_users`)
- Source files (from `incident-tools.plan.md` Task 1/3, full read — extending, not replacing): `mcp_server/config.py`, `mcp_server/server.py` (including the `ArgModelBase` strict-schema patch BEH-2 relies on), `mcp_server/tools/__init__.py`
- Reference source: `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/server.py`, `mcp_server/tools/projects.py` (full read — pattern to mirror, `main()` import wiring already present)
- `.venv/lib/python3.12/site-packages/mcp/server/mcpserver/utilities/func_metadata.py` (in `mock-jira`'s `.venv`) — confirms `ArgModelBase` and `create_model(..., __base__=ArgModelBase, ...)` call site; the patch itself is `incident-tools.plan.md` Task 3's, not reapplied here

### Task 3 Context
- Spec: `.context-index/specs/features/mcp-server/user-tools.spec.md` (BEH-1, BEH-2, BEH-3, Error Cases table — full behavioral contract)
- Task 1/2 (this plan) output: `mcp_server/tools/users.py`, `mcp_server/client.py`
- Source files (from `incident-tools.plan.md` Task 3, full read): `mcp_server/server.py`
- Reference tests: `/Users/dpavancini/Development/adev-course/mock-jira/tests/mcp_server/test_project_tools.py` (full read — fake-client + `mcp.Client`/`call_tool` pattern to adapt)

---

## Parallelization

- Group A (sequential, cross-plan): `incident-tools.plan.md` Task 1 → this plan's Task 1
- Group B (sequential, cross-plan): `incident-tools.plan.md` Task 3 → this plan's Task 2 → Task 3

This plan's Task 1 modifies `mcp_server/client.py`, created by `incident-tools.plan.md` Task 1, so
it cannot start before that task lands (cross-plan dependency). This plan's Task 2 modifies
`mcp_server/server.py` (which already carries the `ArgModelBase` strict-schema patch BEH-2 relies
on), created by `incident-tools.plan.md` Task 3, so it additionally depends on that task. Within
this plan there is no independent group: Task 2 imports `ItsmApiClient` from Task 1's extended
`client.py`, and Task 3's test suite exercises the tool Task 2 registers. All three of this plan's
tasks run in one sequential chain.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | `ItsmApiClient.list_users` HTTP method | small | unit | incident-tools Task 1 (cross-plan) | 0 create, 2 modify |
| 2 | `list_users` tool (strict empty schema) | small | unit | Task 1; incident-tools Task 3 (cross-plan) | 1 create, 1 modify |
| 3 | Unit tests for the list_users tool (BEH-1/2/3) | small | unit | Task 2 | 1 create, 0 modify |

---

## Task Structure

### Task 1: `ItsmApiClient.list_users` HTTP method [specialist: none]

**Charter capability:** `list_users tool`
**Depends on:** `incident-tools.plan.md` Task 1 (cross-plan) — modifies the `mcp_server/client.py`
that task creates
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `mcp_server/client.py` — add `list_users()` to the existing `ItsmApiClient` class
  (created by `incident-tools.plan.md` Task 1; do not recreate the file, `errors.py`, `config.py`,
  or the shared `_request()` helper)
- Test: `tests/mcp_server/test_client.py` — extend (created by `incident-tools.plan.md` Task 1)

**Tests:** `tests/mcp_server/test_client.py` — extend, first task in this plan to touch this
suite; adds unit tests for `list_users` against `httpx.MockTransport` (no real network call),
alongside `incident-tools`' own coverage already in the file, mirroring `mock-jira`'s
`tests/mcp_server/test_client.py`.

**Context to load:**
- Source files (from `incident-tools.plan.md` Task 1, full read — extending, not replacing):
  `mcp_server/client.py`, `mcp_server/errors.py`, `mcp_server/config.py`
- `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/client.py`, `errors.py`, `config.py` (full files — pattern to mirror)
- `.context-index/specs/features/itsm-api/user-directory.spec.md` (upstream response shape and error posture)

- [ ] **Write failing test**

`incident-tools.plan.md` Task 1 already defines a `_client(handler)` helper and the
`httpx`/`pytest`/`ItsmApiClient`/`UpstreamError`/`UpstreamUnreachableError` imports at the top of
`tests/mcp_server/test_client.py` — reuse them; do not redefine.

```python
# tests/mcp_server/test_client.py (append)
@pytest.mark.anyio
async def test_list_users_returns_api_response_unmodified():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/users"
        return httpx.Response(
            200,
            json={
                "items": [{"name": "Rui Bastos", "role": "Support Manager", "assignment_group": None}],
                "page": 1,
                "page_size": 20,
                "total": 1,
            },
        )

    result = await _client(handler).list_users()
    assert result["items"][0]["name"] == "Rui Bastos"


@pytest.mark.anyio
async def test_list_users_5xx_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(500, json={"message": "internal error", "code": "INTERNAL_ERROR"})

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).list_users()
    assert exc_info.value.status_code == 500
    assert exc_info.value.message == "internal error"


@pytest.mark.anyio
async def test_list_users_unreachable_api_raises_upstream_unreachable_error():
    def handler(request):
        raise httpx.ConnectError("Connection refused", request=request)

    with pytest.raises(UpstreamUnreachableError):
        await _client(handler).list_users()
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_client.py`
Expected: FAIL — `AttributeError: 'ItsmApiClient' object has no attribute 'list_users'`, since
`incident-tools.plan.md` Task 1's `ItsmApiClient` does not define this method yet. (This presumes
`incident-tools` Task 1 has already landed — `mcp_server/client.py` and `mcp_server/errors.py`
must exist before this task's failing-test step can even import them.)

- [ ] **Implement**

```python
# mcp_server/client.py (append inside the existing ItsmApiClient class, after its Incident
# methods; the class already imports UpstreamError/UpstreamUnreachableError and defines
# _request() — reuse both, do not redefine)
    async def list_users(self) -> dict:
        response = await self._request("GET", "/users")
        return response.json()
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/mcp_server/test_client.py`
Expected: PASS

- [ ] **Commit**

Branch (create if not already created): `feat/mcp-server/list-users-tool`

```bash
git checkout -b feat/mcp-server/list-users-tool
git add mcp_server/client.py tests/mcp_server/test_client.py
git commit -m "feat(mcp-server): add ItsmApiClient.list_users HTTP method"
```

---

### Task 2: `list_users` tool (strict empty schema) [specialist: none]

**Depends on:** Task 1; `incident-tools.plan.md` Task 3 (cross-plan) — modifies the
`mcp_server/server.py` and `mcp_server/tools/__init__.py` that task creates
**Charter capability:** `list_users tool`
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `mcp_server/server.py` — add `import mcp_server.tools.users` inside `main()` (created
  by `incident-tools.plan.md` Task 3, which already carries the `ArgModelBase`/`extra="forbid"`
  strict-schema patch this task's BEH-2 requirement depends on — do not recreate the `mcp`
  instance or reapply the patch)
- Create: `mcp_server/tools/users.py`
- Test: `tests/mcp_server/test_user_tools.py` (Task 3 authors the full suite; per this spec's TDD cycle, Task 2's implementation and Task 3's tests are written together — see Task 3)

**Tests:** `tests/mcp_server/test_user_tools.py` — new suite (Task 3 creates the file; this task's tool code is what that suite exercises).

**Context to load:**
- `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/server.py`, `mcp_server/tools/projects.py` (full files — pattern to mirror, `main()` import wiring already present)
- Source files (from `incident-tools.plan.md` Task 3, full read — extending, not replacing): `mcp_server/server.py` (including the `ArgModelBase` patch), `mcp_server/tools/__init__.py`
- `.context-index/specs/features/mcp-server/user-tools.spec.md` (BEH-2 — the empty-schema requirement, satisfied by the already-applied `ArgModelBase` patch)

- [ ] **Write failing test**

See Task 3 for the full test file content — write Task 3's failing tests first, per the TDD cycle, then return to this task's implementation.

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/mcp_server/test_user_tools.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_server.tools.users'`, since that
module does not exist yet. (`mcp_server.server`, including the `ArgModelBase` patch, already
exists, created by `incident-tools.plan.md` Task 3.)

- [ ] **Implement**

```python
# mcp_server/server.py — modify main() only; do not touch the mcp instance or the ArgModelBase
# patch, both already present from incident-tools.plan.md Task 3
def main() -> None:
    import mcp_server.tools.incidents  # noqa: F401  (already present, from incident-tools)
    import mcp_server.tools.users  # noqa: F401  (this task's addition)

    from mcp_server.server import mcp as _mcp

    port = os.environ.get("PORT")
    if port:
        _mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        _mcp.run()
```

```python
# mcp_server/tools/users.py
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.client import ItsmApiClient
from mcp_server.config import get_api_base_url
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


def _client() -> ItsmApiClient:
    return ItsmApiClient(get_api_base_url())


@mcp.tool()
async def list_users() -> dict[str, Any]:
    """List all SysUsers in itsm-api's support-team directory, unmodified.

    Declares no input parameters. Per BEH-2, any argument at all fails the tool's (strict,
    empty) input schema and errors before this function body — and therefore any HTTP call —
    ever runs.
    """
    client = _client()
    try:
        return await client.list_users()
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
```

`mcp_server/tools/__init__.py` already exists (created by `incident-tools.plan.md` Task 3).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/mcp_server/test_user_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add mcp_server/server.py mcp_server/tools/users.py
git commit -m "feat(mcp-server): add list_users MCP tool with strict empty input schema"
```

---

### Task 3: Unit tests for the list_users tool (BEH-1/2/3) [specialist: none]

**Depends on:** Task 2
**Charter capability:** `list_users tool`
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `tests/mcp_server/test_user_tools.py`
- Test: `tests/mcp_server/test_user_tools.py` (this file IS the test)

**Tests:** `tests/mcp_server/test_user_tools.py` — mirrors `mock-jira`'s `tests/mcp_server/test_project_tools.py` structure (fake client via `monkeypatch.setattr`, `mcp.Client`/`call_tool`, `structured_content`/`content` assertions). Covers BEH-1 (unmodified passthrough), BEH-2 (strict empty schema, no HTTP call on any input), and BEH-3 (5xx and unreachable-API error passthrough).

**Context to load:**
- `/Users/dpavancini/Development/adev-course/mock-jira/tests/mcp_server/test_project_tools.py` (full file — pattern to copy and adapt)
- `.context-index/specs/features/mcp-server/user-tools.spec.md` (Behaviors, Error Cases table)

- [ ] **Write failing test**

```python
# tests/mcp_server/test_user_tools.py
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
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/mcp_server/test_user_tools.py`
Expected: FAIL until Task 2's implementation exists — Tasks 2 and 3 are executed together per the TDD cycle noted on Task 2 (write these tests first, watch them fail against a missing `mcp_server.tools.users`, then implement Task 2's code to turn them green).

- [ ] **Implement**

(Covered by Task 2's implementation step — this task's file IS the test authored in that cycle.)

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/mcp_server/`
Expected: PASS (`test_client.py` and `test_user_tools.py` both green)

- [ ] **Commit**

```bash
git add tests/mcp_server/test_user_tools.py
git commit -m "test(mcp-server): unit tests for the list_users tool (BEH-1/2/3)"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are recorded in the validation report (`.validate.md`), not in this plan.

Per `.context-index/governance/gates.yaml`:
- Tests pass: `python3 -m pytest -q` (fast tier, error severity)
- Lint passes: `ruff check .` (fast tier, error severity)
- Integration-test gate: unwired sentinel (`command: ""`) — not applicable this milestone
- All acceptance criteria from `user-tools.spec.md` satisfied (BEH-1, BEH-2, BEH-3; no constitutional violations)
