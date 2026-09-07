<!-- partial_schema: plan@1 -->

# Implementation Plan: Incident MCP tools (list/get/create/update)

> **Methodology:** adev
> **Charter:** .context-index/specs/features/mcp-server/charter.md
> **Spec:** .context-index/specs/features/mcp-server/incident-tools.spec.md
> **Review:** PASS (2026-09-07)
> **Platform:** `mcp` Python SDK (official, PyPI `mcp`), `httpx`, Python 3.11 — this is a
> greenfield build of the `mcp_server/` package; neither `mcp_server/` nor `app/` (itsm-api) has
> any code yet in this repo, unlike `mock-jira` where `project-tools` had already stood up the
> package this spec's sibling plan extended.

**Goal:** Stand up the `mcp_server/` package from scratch and implement four MCP tools —
`list_incidents`, `get_incident`, `create_incident`, `update_incident` — that thinly wrap
`itsm-api`'s `/incidents` HTTP endpoints, mirroring `mock-jira`'s `mcp_server/` conventions
(`client.py` HTTP wrapper, `errors.py` typed exceptions, `config.py` env lookup, `server.py`
`MCPServer` registration, `tools/*.py` per-entity tool modules).

**Architecture:** A new `ItsmApiClient` class in `mcp_server/client.py` wraps four HTTP calls
(`GET /incidents`, `GET /incidents/{number}`, `POST /incidents`, `PATCH /incidents/{number}`)
behind a shared `_request()` helper that maps 4xx/5xx responses to `UpstreamError` and network
failures to `UpstreamUnreachableError` (both in `mcp_server/errors.py`, verbatim copies of
`mock-jira`'s pair — the shape already proven to satisfy an identical error-passthrough
contract). `mcp_server/config.py::get_api_base_url()` reads `API_BASE_URL` from the environment,
unchanged from `mock-jira`. `mcp_server/server.py` creates one module-level `MCPServer` instance
named `"mock-servicenow-mcp"` and a `main()` that registers tool modules as a side-effecting
import, using the exact re-import-by-qualified-name pattern `mock-jira/mcp_server/server.py`
documents (avoids the `__main__` vs `mcp_server.server` duplicate-module-instance bug when run as
an entrypoint). `mcp_server/tools/incidents.py` registers the four tools on that shared instance,
using the same `_client()` / `try/except UpstreamError/except UpstreamUnreachableError/finally:
await client.aclose()` shape `mock-jira/mcp_server/tools/issues.py` uses. Per the constitution's
"HTTP contract is the boundary" and "no inbound dependencies," nothing in this plan imports from
`app/` (itsm-api's implementation does not exist yet and is irrelevant to this plan — the
`incident-lifecycle.spec.md` Behavioral Contract is the sole source of truth for request/response
shapes) or opens the SQLite file; every test mocks the HTTP layer via `httpx.MockTransport` (client
layer) or the SDK's in-memory `Client(mcp)` harness (tool layer), never a live server, per
"fixture-backed, offline only."

**Constitution Validation (Step 3):** Checked every task's files/behavior against `Architecture
Boundaries`. No task adds a dependency on another repo in the workspace, touches auth, or defines
a permission/state-transition guard on `update_incident` (Non-Negotiable Principle 5 explicitly
forbids one — Task 5 below is the task that would be tempted to add one, and its entire point is
proving none exists). Adding `mcp`/`httpx`/`anyio`/`pytest`/`ruff` as pip dependencies (Task 1) is
an ordinary internal build step, not a "dependency on another repo in the workspace," so it needs
no human approval. `governance/boundaries.yaml` has `boundaries: []`, so no file-pattern rule
applies. No task in this plan is marked `[REQUIRES HUMAN APPROVAL]`.

**Design decision — no source-manifest, no upstream code to read:** Unlike `mock-jira`'s
`issue-tools.plan.md`, this plan cannot cite `app/routers/incidents.py` or `app/models.py` as
reference material because `itsm-api` has no implementation yet (only a `review-passed` spec).
Every field name, endpoint shape, status code, and error condition below is sourced from
`incident-lifecycle.spec.md`'s Behavioral Contract and the `itsm-api` charter's Domain Model
table, not from code. `incident-lifecycle.plan.md` does not exist to inherit a pagination
envelope or error-body shape from either. Two shape assumptions this plan therefore makes
explicit (both low-risk because `list_incidents`/error passthrough are contractually required to
be verbatim, so an actual shape mismatch would surface as an easily-diagnosed integration
failure against the real `itsm-api`, never a silent bug):
- **Pagination parameters are named `page`/`per_page`** (optional `int`), forwarded as opaque
  query parameters. This is safe because BEH-1 requires `list_incidents` to return the API's
  response "unmodified" — the tool never parses or asserts on the envelope shape, so a real-world
  name mismatch (e.g. `itsm-api` ultimately using `limit`/`offset`) would only require renaming
  two keyword arguments here, not restructuring any test.
- **Error bodies are `{"message": ..., "code": ...}`**, matching `mock-jira`'s (and this repo's
  own `itsm-api` charter Quality Attributes: "Errors return JSON with a message naming what was
  rejected and why") convention. `_request()` reads `body.get("message", response.text)`, so even
  an unexpected error-body shape degrades to using the raw response text rather than crashing.

**Design decision — `state`/`priority`/`category` stay unconstrained (`str`/`int`, not
`Literal`/ranged):** `incident-lifecycle.spec.md` BEH-7 makes `itsm-api` the sole enforcer of the
five valid `state` values, the four valid `priority` values (1-4), and the eight valid `category`
values — this spec's own BEH-4b/BEH-8 require an invalid value to reach `itsm-api` and come back
as a `422` passed through verbatim (`MCP_UPSTREAM_ERROR`), not be rejected by the tool's own
schema as `MCP_INPUT_INVALID`. If `state`/`category` were typed as MCP-schema `Literal[...]` or
`priority` as a range-constrained int, an invalid value would never leave the MCP layer, making
BEH-4b/BEH-8 unreachable/untestable through this path — the same tension `mock-jira`'s
`issue-tools.plan.md` resolved for `issue_type`/`priority`/`status`. This plan makes the identical
choice: `category`, `state` are plain `str`; `priority` is plain `int` (shape-checked — a
non-integer still fails BEH-9 before any HTTP call — but not range-checked). `account_id`,
`short_description`, `description` remain required, unconstrained `str` whose *absence* (not
invalid value) is what the MCP SDK's own required-argument validation catches for BEH-9.

**Design decision — `ItsmApiClient` is one class, sized for this spec's four methods but named
for the whole API:** The charter's Capability Map lists five more tool capabilities
(`list_work_notes`, `add_work_note`, `list_escalations`, `list_sla_records`, `list_users`) as
separate, not-yet-planned Live Specs. Naming the client class `ItsmApiClient` (not
`IncidentClient`) means a future spec's plan extends this same class with more methods, exactly as
`mock-jira`'s `IssueTrackerClient` gained `create_issue`/`update_issue`/`delete_issue` in a later
plan without a rename. This plan implements only the four Incident methods; no other entity's
methods are added here.

**Shared-foundation note — this plan is the canonical foundation owner for `mcp_server/`:** Four
`mcp-server` plans were authored independently against the same greenfield package —
`incident-tools` (this plan), `work-note-tools`, `escalation-and-sla-tools`, and `user-tools` —
and each originally drafted its own copy of `mcp_server/config.py`, `mcp_server/errors.py`,
`mcp_server/client.py`, `mcp_server/server.py`, and `requirements.txt`/`pytest.ini`. Since all four
build against one package, exactly one plan may actually create these files; the other three now
extend them (adding their own `ItsmApiClient` methods and their own `mcp_server/tools/<name>.py`
module, and adding one `import mcp_server.tools.<name>` line to `server.py`'s `main()`) rather than
recreating them. This plan is that one owner: Task 1 creates `mcp_server/__init__.py`,
`config.py`, `errors.py`, `client.py` (read methods), `requirements.txt`, `pytest.ini`, and the
`tests/mcp_server/` scaffold; Task 3 creates `mcp_server/server.py` (the shared `mcp` instance,
the `ArgModelBase` strict-schema patch below, and `main()`) and `mcp_server/tools/__init__.py`.
Every sibling plan's first task now carries a `Depends on: incident-tools Task 1 (cross-plan)` (or
Task 3, where it needs the tool-registration scaffold) annotation.

**Design decision — `server.py` carries the `ArgModelBase`/`extra="forbid"` strict-schema patch,
applied once, here:** `user-tools.spec.md` BEH-2 requires `list_users` (a zero-parameter tool) to
reject any argument before an HTTP call is made. The installed `mcp` SDK's auto-generated per-tool
argument model (`ArgModelBase`, in `mcp.server.mcpserver.utilities.func_metadata`) defaults to
pydantic's `extra="ignore"`, so a zero-parameter tool would otherwise silently drop unexpected
arguments and proceed to the real HTTP call — violating BEH-2. This was confirmed against the
installed `mcp` SDK's source in `mock-jira`'s `.venv` (`mcp/server/mcpserver/utilities/
func_metadata.py`, `mcp/server/mcpserver/tools/base.py`, the exact investigation `user-tools.
plan.md` ran independently): `Tool.from_function` calls `func_arg_metadata.arg_model.
model_json_schema(by_alias=True)` with no other hook to inject `extra="forbid"` per tool, and
`create_model(..., __base__=ArgModelBase, ...)` is the single construction point every tool's
argument model inherits from. Because every `mcp-server` tool spec's tools share one `mcp`
instance, this fix belongs on the shared `ArgModelBase` class itself, applied exactly once,
immediately after constructing `mcp = MCPServer(...)` in `mcp_server/server.py` (Task 3) and before
any tool module is imported — not repeated per tool module. This makes every tool's input schema
strict (`additionalProperties: false` in the published JSON schema, a `pydantic.ValidationError`
on an unknown key at validation time) for every tool this plan and every sibling plan registers,
including `list_users`.

---

## File Structure

**Create:**
- `mcp_server/__init__.py` — empty, makes `mcp_server` a package (no code from any prior spec
  exists in this repo to already provide this) — **shared foundation file; every sibling
  `mcp-server` tool plan depends on this existing rather than creating its own**
- `mcp_server/config.py` — `get_api_base_url()`, verbatim copy of `mock-jira`'s — **shared
  foundation file (see above)**
- `mcp_server/errors.py` — `UpstreamError`, `UpstreamUnreachableError`, verbatim copy of
  `mock-jira`'s — **shared foundation file (see above)**
- `mcp_server/client.py` — `ItsmApiClient` with `list_incidents`, `get_incident`,
  `create_incident`, `update_incident`, and the shared `_request()` helper — **shared foundation
  file: sibling plans add their own methods to this same class (`list_work_notes`/`add_work_note`,
  `list_escalations`/`list_sla_records`, `list_users`), never a separate client**
- `mcp_server/server.py` — module-level `MCPServer("mock-servicenow-mcp")` instance, the
  `ArgModelBase`/`extra="forbid"` strict-schema patch (applied once, before any tool module is
  imported — see design decision above), and `main()` — **shared foundation file: every sibling
  plan extends `main()` with one `import mcp_server.tools.<name>` line, never by recreating this
  file**
- `mcp_server/tools/__init__.py` — empty, makes `mcp_server.tools` a package — **shared foundation
  file (see above)**
- `mcp_server/tools/incidents.py` — registers the four tools on the shared `mcp` instance
- `tests/mcp_server/__init__.py` — empty — **shared foundation file (see above)**
- `tests/mcp_server/conftest.py` — `anyio_backend` fixture, verbatim copy of `mock-jira`'s —
  **shared foundation file (see above)**
- `tests/mcp_server/test_client.py` — `ItsmApiClient` HTTP-wrapper-layer coverage (BEH-1 through
  BEH-8, error-passthrough rows) — sibling plans extend this same file with their own methods'
  coverage
- `tests/mcp_server/test_incident_tools.py` — tool-layer coverage (BEH-1 through BEH-10,
  including the dedicated BEH-6 no-guard regression test)
- `requirements.txt` — `mcp`, `httpx`, `anyio`, `pytest`, `ruff` (no pip requirements file exists
  anywhere in this repo yet; `itsm-api`'s own deps — `fastapi`, `uvicorn`, `pydantic` — are out of
  scope for this plan and added by whichever plan first implements `app/`) — **shared foundation
  file (see above); this is the single canonical dependency file every `mcp_server/**` plan and
  `mcp-e2e.plan.md`'s `requirements-e2e.txt` builds on — no plan in this module introduces a
  separate `requirements-mcp.txt`**
- `pytest.ini` — `[pytest]\ntestpaths = tests`, verbatim copy of `mock-jira`'s — **shared
  foundation file (see above)**

**Modify:**
- None — every file this plan touches is newly created; there is no existing `mcp_server/` or
  `tests/` tree in this repo to extend.

**Reference (read, do not modify):**
- `.context-index/specs/features/itsm-api/incident-lifecycle.spec.md` — the sole source of truth
  for `itsm-api`'s `/incidents` request/response shapes, status codes, and field names (no
  `app/` code exists to read instead)
- `.context-index/specs/features/itsm-api/charter.md` — Domain Model's `Incident` entity row
  (exact field list: `number`, `account_id`, `category`, `short_description`, `description`,
  `state`, `priority`, `opened_at`, `resolved_at`, `assigned_to`, `assignment_group`, `escalated`)
- `.context-index/specs/features/itsm-api/sla-records.spec.md` — `TaskSla` shape
  (`incident_number`, `sla_definition`, `target_minutes`, `actual_minutes`, `has_breached`,
  `business_time_only`) needed to construct the BEH-6 no-guard test's breached-SLA fixture
- `.context-index/specs/features/mcp-server/charter.md` — Capability Map (four Incident tool
  rows), Domain Model (`McpTool` entity), Invariants ("input_schema validates before the wrapped
  HTTP call", "error response always carries the underlying API's error message verbatim", "no
  McpTool call is refused on the grounds of what state it would produce")
- `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/client.py`,
  `mcp_server/config.py`, `mcp_server/errors.py`, `mcp_server/server.py`,
  `mcp_server/tools/issues.py` — exact style/shape exemplars for every file this plan creates
- `.venv`/site-packages `mcp/server/mcpserver/utilities/func_metadata.py`,
  `mcp/server/mcpserver/tools/base.py` (in `mock-jira`'s `.venv`, since `mock-servicenow` has no
  venv yet) — confirms `ArgModelBase` has no `extra="forbid"` by default and that
  `Tool.from_function` offers no other injection point for a strict schema; this is the basis for
  Task 3's `server.py` patch (the same investigation `user-tools.plan.md` ran independently)
- `/Users/dpavancini/Development/adev-course/mock-jira/tests/mcp_server/test_client.py`,
  `tests/mcp_server/test_issue_tools.py`, `tests/mcp_server/conftest.py` — exact test-shape
  exemplars (the `_client(handler)` helper, `_FakeClient` monkeypatch pattern, parametrized
  unreachable-API test)
- `CLAUDE.md` — constitution: "The HTTP contract is the boundary", "No inbound dependencies",
  "The MCP tools stay unguarded" (Principle 5 — directly governs Task 5), "Seeded discrepancies
  are load-bearing, not bugs" (Principle 6 — the reason Task 5's BEH-6 test exists at all)
- `.context-index/governance/gates.yaml` — authoritative quality-gate commands

---

## Context Packets

> No `source-manifest.files[]` exists on this spec yet (this is its first implementation pass).
> Context packets fall back to charter + spec + constitution + the sibling `incident-lifecycle`
> spec (as the HTTP contract) + the `mock-jira` exemplar files, per Step 2's "no source-manifest"
> fallback.

### Task 1 Context
- Spec: BEH-1, BEH-2, BEH-3, Error Cases table (404 row)
- Charter (mcp-server): Capability `list_incidents tool`, `get_incident tool`; Invariants (error
  passthrough)
- `incident-lifecycle.spec.md`: BEH-1, BEH-2, BEH-3, BEH-4 (full read — exact filter param names,
  Incident field list, 404 body)
- Exemplar (full read): `mock-jira/mcp_server/client.py`, `mock-jira/mcp_server/config.py`,
  `mock-jira/mcp_server/errors.py`, `mock-jira/tests/mcp_server/test_client.py`,
  `mock-jira/tests/mcp_server/conftest.py`, `mock-jira/pytest.ini`, `mock-jira/requirements.txt`

### Task 2 Context
- Spec: BEH-4, BEH-4b, BEH-5, BEH-6, BEH-7, BEH-8, Preconditions (`number` immutability), Error
  Cases table (all rows)
- Charter (mcp-server): Capability `create_incident tool`, `update_incident tool`
- `incident-lifecycle.spec.md`: BEH-5 (full read — six required create fields, defaults), BEH-7
  (invalid state/priority → 422), BEH-8 (PATCH mutable fields, immutable fields silently ignored),
  BEH-9 (404 on unknown number)
- `sla-records.spec.md`: TaskSla field shape (for constructing a believable breached-SLA fixture
  used later at the tool layer)
- Source files (from Task 1, full read): `mcp_server/client.py`, `mcp_server/errors.py`

### Task 3 Context
- Spec: BEH-1, BEH-2, BEH-3, BEH-9
- Charter (mcp-server): Capability `list_incidents tool`, `get_incident tool`; Exposed APIs table
- Source files (from Task 1, full read): `mcp_server/client.py`
- Exemplar (full read): `mock-jira/mcp_server/tools/issues.py` (the `_client()` / `@mcp.tool()` /
  error-mapping pattern to replicate), `mock-jira/mcp_server/server.py` (the re-import-by-
  qualified-name `main()` pattern)

### Task 4 Context
- Spec: BEH-4, BEH-4b, Error Cases table (`MCP_INPUT_INVALID` row, 422 row)
- Charter (mcp-server): Capability `create_incident tool`
- Design decision (plan header): `category`/`state` stay unconstrained `str`, `priority` stays
  unconstrained `int` — no defaults, all six fields required
- Source files (from Task 3, full read — extending, not replacing): `mcp_server/tools/incidents.py`,
  `tests/mcp_server/test_incident_tools.py`

### Task 5 Context
- Spec: BEH-5, BEH-6, BEH-7, BEH-8, BEH-9, Postconditions ("update_incident's success is never
  conditional on the resulting state being 'safe'"), the charter's Non-Negotiable Principle 5 and
  the mcp-server charter's Domain Model Invariant ("No McpTool call is refused on the grounds of
  what state it would produce")
- Actionable Task Map row: "Confirm no guard exists — a regression here would silently violate
  Principle 5"
- `sla-records.spec.md` BEH-7 (`business_time_only`/`has_breached` field shape for the fixture)
- Source files (from Task 4, full read — extending): `mcp_server/tools/incidents.py`,
  `tests/mcp_server/test_incident_tools.py`

### Task 6 Context
- Spec: Error Cases table (`MCP_UPSTREAM_UNREACHABLE` row and `5xx` row, all four tools), BEH-10
- Charter (mcp-server): Quality Attributes → Observability ("Tool errors surface the underlying
  API error message unchanged")
- Exemplar (full read): `mock-jira/tests/mcp_server/test_issue_tools.py` Task 7 (the parametrized
  unreachable-API test across every tool)
- Source files (from Task 1-5, full read — verifying only, no expected production-code change):
  `mcp_server/client.py`, `mcp_server/tools/incidents.py`

---

## Parallelization

- Group A (sequential): Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6

Every task modifies a file the immediately preceding task also touched or extended: Tasks 1 and 2
both build `mcp_server/client.py`/`tests/mcp_server/test_client.py` from scratch, then extend
them; Tasks 3-6 all extend `mcp_server/tools/incidents.py`/`tests/mcp_server/test_incident_tools.py`
(Task 3 creates both files). There is no file-disjoint pair of tasks in this plan, so no group can
run independently of another.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Package scaffold + `ItsmApiClient` read methods (`list_incidents`, `get_incident`) | medium | unit | — | 10 create, 0 modify |
| 2 | `ItsmApiClient` write methods (`create_incident`, `update_incident`) | medium | unit | Task 1 | 0 create, 2 modify |
| 3 | `list_incidents` + `get_incident` tools | medium | unit | Task 1, Task 2 | 3 create, 1 modify |
| 4 | `create_incident` tool | medium | unit | Task 3 | 0 create, 2 modify |
| 5 | `update_incident` tool [Confirm no guard exists] | medium | unit | Task 4 | 0 create, 2 modify |
| 6 | [Regression] Confirm unreachable/5xx passthrough (all four tools) | small | unit | Task 5 | 0 create, 2 modify |

All tasks resolve to the `unit` strategy (source: fallback — no `test_strategy` in spec
frontmatter, no `test_strategies` entries in `manifest.yaml` matching `mcp_server/**` paths). Per
Step 5, the Strategy Summary section is omitted since every task is `unit`. No
`infra_requirements:` is declared on the spec and no task needs external infrastructure — every
test in this plan runs against `httpx.MockTransport` or the SDK's own in-memory `Client(mcp)`
harness, never a live server (neither `itsm-api` nor `mcp-server` has a running process anywhere
in this plan) — so the Test Infrastructure Requirements section is also omitted.

**Granularity:** `per-behavior` (source: manifest — `test_policy.granularity: per-behavior` in
`.context-index/manifest.yaml`). `tests/mcp_server/test_client.py` is the shared per-behavior
suite for the HTTP-wrapper layer: created by Task 1 (BEH-1/2/3 + 404 row), extended by Task 2
(BEH-4/4b/5/6/7/8). `tests/mcp_server/test_incident_tools.py` is the shared per-behavior suite for
the tool layer: created by Task 3 (BEH-1/2/3/9), extended by Task 4 (BEH-4/4b), Task 5
(BEH-5/6/7/8/9), and Task 6 (the shared BEH-10 unreachable/5xx row).

---

## Task Structure

### Task 1: Package scaffold + `ItsmApiClient` read methods (`list_incidents`, `get_incident`) [specialist: none]

**Charter capability:** `list_incidents` tool, `get_incident` tool (HTTP-wrapper layer)
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `mcp_server/__init__.py`
- Create: `mcp_server/config.py`
- Create: `mcp_server/errors.py`
- Create: `mcp_server/client.py` — `ItsmApiClient.list_incidents`, `ItsmApiClient.get_incident`,
  `_request()`
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `tests/mcp_server/__init__.py`
- Create: `tests/mcp_server/conftest.py`
- Test: `tests/mcp_server/test_client.py`

**Tests:** `tests/mcp_server/test_client.py` (create — first task to touch this behavior; covers
BEH-1, BEH-2, BEH-3, and the 404 Error Cases row at the HTTP-wrapper layer)

**Context to load:**
- Spec BEH-1, BEH-2, BEH-3, Error Cases table (404 row)
- `incident-lifecycle.spec.md` BEH-1 through BEH-4 (exact filter names, Incident fields, 404 body)
- `mock-jira/mcp_server/client.py`, `config.py`, `errors.py`, `tests/mcp_server/test_client.py`,
  `conftest.py`, `pytest.ini`, `requirements.txt` (style exemplars)

- [ ] **Write failing test**

```python
# requirements.txt
mcp
httpx
anyio
pytest
ruff
```

```ini
# pytest.ini
[pytest]
testpaths = tests
```

```python
# mcp_server/__init__.py
```

```python
# mcp_server/config.py
import os


def get_api_base_url() -> str:
    value = os.environ.get("API_BASE_URL")
    if not value:
        raise RuntimeError(
            "API_BASE_URL environment variable is required to reach itsm-api"
        )
    return value
```

```python
# mcp_server/errors.py
class UpstreamError(Exception):
    """itsm-api returned an HTTP error response (4xx/5xx)."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class UpstreamUnreachableError(Exception):
    """itsm-api could not be reached at all (connection refused, DNS, timeout)."""
```

```python
# tests/mcp_server/__init__.py
```

```python
# tests/mcp_server/conftest.py
import pytest


@pytest.fixture
def anyio_backend():
    return "asyncio"
```

```python
# tests/mcp_server/test_client.py
import httpx
import pytest

from mcp_server.client import ItsmApiClient
from mcp_server.errors import UpstreamError


def _client(handler):
    return ItsmApiClient("http://itsm-api", transport=httpx.MockTransport(handler))


_SAMPLE_INCIDENT = {
    "number": "TICKET-004417", "account_id": "ACCOUNT-1001", "category": "billing",
    "short_description": "Invoice mismatch", "description": "Customer reports a mismatch.",
    "state": "new", "priority": 2, "opened_at": "2026-09-01T00:00:00Z", "resolved_at": None,
    "assigned_to": None, "assignment_group": "Support Tier 1", "escalated": False,
}


@pytest.mark.anyio
async def test_list_incidents_returns_api_response_unmodified():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/incidents"
        return httpx.Response(200, json={"items": [_SAMPLE_INCIDENT], "page": 1})

    result = await _client(handler).list_incidents()
    assert result == {"items": [_SAMPLE_INCIDENT], "page": 1}


@pytest.mark.anyio
async def test_list_incidents_passes_filters_and_pagination_as_query_params():
    def handler(request):
        params = request.url.params
        assert params["account_id"] == "ACCOUNT-1001"
        assert params["state"] == "new"
        assert params["category"] == "billing"
        assert params["opened_after"] == "2026-08-01"
        assert params["opened_before"] == "2026-09-01"
        assert params["escalated"] == "true"
        assert params["page"] == "2"
        assert params["per_page"] == "50"
        return httpx.Response(200, json={"items": [], "page": 2})

    await _client(handler).list_incidents(
        account_id="ACCOUNT-1001", state="new", category="billing",
        opened_after="2026-08-01", opened_before="2026-09-01", escalated=True,
        page=2, per_page=50,
    )


@pytest.mark.anyio
async def test_get_incident_returns_the_incident():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/incidents/TICKET-004417"
        return httpx.Response(200, json=_SAMPLE_INCIDENT)

    result = await _client(handler).get_incident("TICKET-004417")
    assert result["number"] == "TICKET-004417"


@pytest.mark.anyio
async def test_get_incident_unknown_number_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(
            404,
            json={"message": "Incident TICKET-999999 not found", "code": "INCIDENT_NOT_FOUND"},
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).get_incident("TICKET-999999")
    assert exc_info.value.status_code == 404
    assert exc_info.value.message == "Incident TICKET-999999 not found"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_client.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_server'`, since none of the package
files exist yet.

- [ ] **Implement**

```python
# mcp_server/client.py
import httpx

from mcp_server.errors import UpstreamError, UpstreamUnreachableError


class ItsmApiClient:
    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None):
        self._http = httpx.AsyncClient(base_url=base_url, transport=transport)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def list_incidents(
        self,
        account_id: str | None = None,
        state: str | None = None,
        category: str | None = None,
        opened_after: str | None = None,
        opened_before: str | None = None,
        escalated: bool | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> dict:
        params: dict = {}
        if account_id is not None:
            params["account_id"] = account_id
        if state is not None:
            params["state"] = state
        if category is not None:
            params["category"] = category
        if opened_after is not None:
            params["opened_after"] = opened_after
        if opened_before is not None:
            params["opened_before"] = opened_before
        if escalated is not None:
            params["escalated"] = escalated
        if page is not None:
            params["page"] = page
        if per_page is not None:
            params["per_page"] = per_page
        response = await self._request("GET", "/incidents", params=params)
        return response.json()

    async def get_incident(self, number: str) -> dict:
        response = await self._request("GET", f"/incidents/{number}")
        return response.json()

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            response = await self._http.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise UpstreamUnreachableError(
                f"Could not reach itsm-api at {self._http.base_url}: {exc}"
            ) from exc
        if response.status_code >= 400:
            body = response.json()
            message = body.get("message", response.text)
            raise UpstreamError(response.status_code, message)
        return response
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_client.py`
Expected: PASS

- [ ] **Commit**

Branch (if not already created): `feat/mcp-server/incident-tools`

```bash
git add mcp_server/__init__.py mcp_server/config.py mcp_server/errors.py mcp_server/client.py \
  requirements.txt pytest.ini tests/mcp_server/__init__.py tests/mcp_server/conftest.py \
  tests/mcp_server/test_client.py
git commit -m "feat(mcp-server): scaffold mcp_server package with ItsmApiClient read methods"
```

---

### Task 2: `ItsmApiClient` write methods (`create_incident`, `update_incident`) [specialist: none]

**Charter capability:** `create_incident` tool, `update_incident` tool (HTTP-wrapper layer)
**Depends on:** Task 1
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `mcp_server/client.py` — add `create_incident`, `update_incident`
- Test: `tests/mcp_server/test_client.py` — extend

**Tests:** `tests/mcp_server/test_client.py` (extend — BEH-4, BEH-4b, BEH-5, BEH-6, BEH-7, BEH-8;
suite already created by Task 1)

**Context to load:**
- Spec BEH-4, BEH-4b, BEH-5, BEH-6, BEH-7, BEH-8, Preconditions (`number` immutability), Error
  Cases table (all rows)
- `incident-lifecycle.spec.md` BEH-5 (six required create fields), BEH-7 (422 on invalid
  state/priority), BEH-8 (PATCH mutable fields, immutable fields ignored), BEH-9 (404 on unknown
  number)

- [ ] **Write failing test**

```python
# tests/mcp_server/test_client.py (append)
@pytest.mark.anyio
async def test_create_incident_sends_all_six_required_fields_and_returns_created_incident():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/incidents"
        import json as _json
        body = _json.loads(request.content)
        assert body == {
            "account_id": "ACCOUNT-1001", "category": "billing",
            "short_description": "Invoice mismatch", "description": "Customer reports a mismatch.",
            "state": "new", "priority": 2,
        }
        return httpx.Response(201, json={**_SAMPLE_INCIDENT, "number": "TICKET-004500"})

    result = await _client(handler).create_incident(
        account_id="ACCOUNT-1001", category="billing",
        short_description="Invoice mismatch", description="Customer reports a mismatch.",
        state="new", priority=2,
    )
    assert result["number"] == "TICKET-004500"


@pytest.mark.anyio
async def test_create_incident_invalid_category_raises_upstream_error_for_422():
    def handler(request):
        return httpx.Response(
            422,
            json={
                "message": "category must be one of: receiving, putaway, picking, cycle-count, "
                           "billing, integrations, auth, reporting",
                "code": "VALIDATION_ERROR",
            },
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).create_incident(
            account_id="ACCOUNT-1001", category="not-a-real-category",
            short_description="x", description="y", state="new", priority=2,
        )
    assert exc_info.value.status_code == 422


@pytest.mark.anyio
async def test_update_incident_sends_only_provided_mutable_fields_and_returns_result():
    def handler(request):
        assert request.method == "PATCH"
        assert request.url.path == "/incidents/TICKET-004417"
        import json as _json
        body = _json.loads(request.content)
        assert body == {"state": "resolved"}
        assert "number" not in body
        return httpx.Response(200, json={**_SAMPLE_INCIDENT, "state": "resolved"})

    result = await _client(handler).update_incident("TICKET-004417", state="resolved")
    assert result["state"] == "resolved"


@pytest.mark.anyio
async def test_update_incident_unknown_number_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(
            404, json={"message": "Incident TICKET-999999 not found", "code": "INCIDENT_NOT_FOUND"}
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).update_incident("TICKET-999999", state="resolved")
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_update_incident_invalid_state_raises_upstream_error_for_422():
    def handler(request):
        return httpx.Response(
            422,
            json={
                "message": "state must be one of: new, in_progress, on_hold, resolved, closed",
                "code": "VALIDATION_ERROR",
            },
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).update_incident("TICKET-004417", state="not-a-real-state")
    assert exc_info.value.status_code == 422
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_client.py`
Expected: FAIL — `AttributeError: 'ItsmApiClient' object has no attribute 'create_incident'` (and
`'update_incident'`), since neither method exists yet.

- [ ] **Implement**

```python
# mcp_server/client.py (append inside ItsmApiClient, after get_incident)
    async def create_incident(
        self,
        account_id: str,
        category: str,
        short_description: str,
        description: str,
        state: str,
        priority: int,
    ) -> dict:
        payload = {
            "account_id": account_id,
            "category": category,
            "short_description": short_description,
            "description": description,
            "state": state,
            "priority": priority,
        }
        response = await self._request("POST", "/incidents", json=payload)
        return response.json()

    async def update_incident(
        self,
        number: str,
        state: str | None = None,
        priority: int | None = None,
        assigned_to: str | None = None,
        assignment_group: str | None = None,
    ) -> dict:
        payload = {}
        if state is not None:
            payload["state"] = state
        if priority is not None:
            payload["priority"] = priority
        if assigned_to is not None:
            payload["assigned_to"] = assigned_to
        if assignment_group is not None:
            payload["assignment_group"] = assignment_group
        response = await self._request("PATCH", f"/incidents/{number}", json=payload)
        return response.json()
```

`create_incident` takes all six required fields as named, non-optional keyword parameters — no
default values, satisfying BEH-4's "no default for either `state` or `priority`" (or any other
field) exactly. `update_incident` builds its PATCH body only from the four mutable fields that
are explicitly passed; `number` is consumed solely as the URL path segment and is structurally
incapable of appearing in the payload dict, satisfying the Preconditions clause that `number` is
"silently ignored if present" — there is no code path by which it could leak into the body.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_client.py`
Expected: PASS

- [ ] **Commit**

```bash
git add mcp_server/client.py tests/mcp_server/test_client.py
git commit -m "feat(mcp-server): add ItsmApiClient.create_incident and update_incident"
```

---

### Task 3: `list_incidents` + `get_incident` tools [specialist: none]

**Charter capability:** `list_incidents` tool — wraps `GET /incidents`; `get_incident` tool —
wraps `GET /incidents/{number}`
**Depends on:** Task 1, Task 2
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `mcp_server/tools/__init__.py`
- Create: `mcp_server/tools/incidents.py`
- Create: `tests/mcp_server/test_incident_tools.py`
- Modify: `mcp_server/server.py` — create the shared `mcp` instance and `main()`

**Tests:** `tests/mcp_server/test_incident_tools.py` (create — first task to touch this behavior;
covers BEH-1, BEH-2, BEH-3, and BEH-9 for `list_incidents`/`get_incident`)

**Context to load:**
- Spec BEH-1, BEH-2, BEH-3, BEH-9
- Charter Capability Map: `list_incidents tool | Wraps GET /incidents`, `get_incident tool | Wraps
  GET /incidents/{number}`
- `mock-jira/mcp_server/tools/issues.py`, `mock-jira/mcp_server/server.py` (pattern to replicate)
- `mcp_server/client.py` (current state, full read)
- `.venv`/site-packages `mcp/server/mcpserver/utilities/func_metadata.py`,
  `mcp/server/mcpserver/tools/base.py` (in `mock-jira`'s `.venv`) — confirms `ArgModelBase` and the
  `create_model(..., __base__=ArgModelBase, ...)` call site, needed to write the strict-schema
  patch below correctly (this file's `server.py` is the one and only place it is applied)

- [ ] **Write failing test**

```python
# mcp_server/server.py
import os

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase
from pydantic import ConfigDict

mcp = MCPServer("mock-servicenow-mcp")

# Strict-schema patch (see plan header design decision): the installed mcp SDK's auto-generated
# per-tool argument model does not set extra="forbid" by default (pydantic v2's own default is
# extra="ignore"), so a zero-parameter tool (e.g. user-tools.spec.md's list_users) would otherwise
# silently drop unexpected arguments and proceed to the real HTTP call instead of erroring first.
# Tightening the shared ArgModelBase every generated argument model inherits from makes every
# tool's input schema strict — an unknown key is rejected at validation time, before the tool body
# (and therefore any HTTP call) ever runs, and the published JSON schema carries
# additionalProperties: false. This must run before any tool module is imported, since each
# @mcp.tool()-decorated function builds its argument model at decoration time. Applied once, here
# — sibling tool modules (work_notes, escalations, sla, users) rely on this already being in
# place; none of them re-apply it.
ArgModelBase.model_config = ConfigDict(extra="forbid")


def main() -> None:
    # Each mcp-server tool plan (incident-tools, work-note-tools, escalation-and-sla-tools,
    # user-tools) adds its own import line here as a side-effecting registration step; the line
    # below is incident-tools' own contribution to the shared list.
    import mcp_server.tools.incidents  # noqa: F401  (import registers the tools as a side effect)

    # See mock-jira/mcp_server/server.py for why this re-import-by-qualified-name is required:
    # running this file as `python -m mcp_server.server` loads it into sys.modules as `__main__`,
    # a separate module object from `mcp_server.server`. The tool modules' absolute imports
    # (`from mcp_server.server import mcp`) trigger a second, independent import of this file
    # under its real package name, registering every @mcp.tool() onto *that* instance instead of
    # the `__main__`-local `mcp` global above.
    from mcp_server.server import mcp as _mcp

    port = os.environ.get("PORT")
    if port:
        _mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        _mcp.run()


if __name__ == "__main__":
    main()
```

```python
# tests/mcp_server/test_incident_tools.py
import pytest
from mcp import Client

import mcp_server.tools.incidents as incidents_tools
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


class _FakeClient:
    """Stands in for ItsmApiClient — Tasks 1/2 already cover the real HTTP wiring."""

    def __init__(self, incidents=None, incident=None):
        self._incidents = incidents if incidents is not None else {"items": []}
        self._incident = incident

    async def list_incidents(self, **kwargs):
        return self._incidents

    async def get_incident(self, number):
        return self._incident

    async def aclose(self):
        pass


_SAMPLE_INCIDENT = {
    "number": "TICKET-004417", "account_id": "ACCOUNT-1001", "category": "billing",
    "short_description": "Invoice mismatch", "description": "Customer reports a mismatch.",
    "state": "new", "priority": 2, "opened_at": "2026-09-01T00:00:00Z", "resolved_at": None,
    "assigned_to": None, "assignment_group": "Support Tier 1", "escalated": False,
}


@pytest.mark.anyio
async def test_list_incidents_tool_returns_api_result_unmodified(monkeypatch):
    fake = _FakeClient(incidents={"items": [_SAMPLE_INCIDENT], "page": 1})
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_incidents", {})

    assert result.is_error is False
    assert result.structured_content == {"items": [_SAMPLE_INCIDENT], "page": 1}


@pytest.mark.anyio
async def test_get_incident_tool_returns_the_incident(monkeypatch):
    monkeypatch.setattr(incidents_tools, "_client", lambda: _FakeClient(incident=_SAMPLE_INCIDENT))

    async with Client(mcp) as client:
        result = await client.call_tool("get_incident", {"number": "TICKET-004417"})

    assert result.is_error is False
    assert result.structured_content == _SAMPLE_INCIDENT


class _NotFoundGetClient(_FakeClient):
    async def get_incident(self, number):
        raise UpstreamError(404, "Incident TICKET-999999 not found")


@pytest.mark.anyio
async def test_get_incident_tool_unknown_number_errors_with_verbatim_message(monkeypatch):
    monkeypatch.setattr(incidents_tools, "_client", lambda: _NotFoundGetClient())

    async with Client(mcp) as client:
        result = await client.call_tool("get_incident", {"number": "TICKET-999999"})

    assert result.is_error is True
    assert "Incident TICKET-999999 not found" in result.content[0].text


@pytest.mark.anyio
async def test_get_incident_tool_missing_number_errors_before_http_request(monkeypatch):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeClient()

    monkeypatch.setattr(incidents_tools, "_client", _client_spy)

    async with Client(mcp) as client:
        result = await client.call_tool("get_incident", {})  # missing required "number"

    assert result.is_error is True
    assert called["value"] is False  # schema validation rejected the call before _client() ran


@pytest.mark.anyio
async def test_list_incidents_tool_invalid_priority_type_errors_before_http_request(monkeypatch):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeClient()

    monkeypatch.setattr(incidents_tools, "_client", _client_spy)

    async with Client(mcp) as client:
        # "escalated" is declared bool; a non-boolean string fails schema validation.
        result = await client.call_tool("list_incidents", {"escalated": "not-a-bool"})

    assert result.is_error is True
    assert called["value"] is False
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_incident_tools.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_server.tools'`, since the tools
package does not exist yet.

- [ ] **Implement**

```python
# mcp_server/tools/__init__.py
```

```python
# mcp_server/tools/incidents.py
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.client import ItsmApiClient
from mcp_server.config import get_api_base_url
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


def _client() -> ItsmApiClient:
    return ItsmApiClient(get_api_base_url())


@mcp.tool()
async def list_incidents(
    account_id: str | None = None,
    state: str | None = None,
    category: str | None = None,
    opened_after: str | None = None,
    opened_before: str | None = None,
    escalated: bool | None = None,
    page: int | None = None,
    per_page: int | None = None,
) -> dict[str, Any]:
    """List Incidents known to itsm-api, filtered and paginated per the given arguments."""
    client = _client()
    try:
        return await client.list_incidents(
            account_id=account_id, state=state, category=category,
            opened_after=opened_after, opened_before=opened_before, escalated=escalated,
            page=page, per_page=per_page,
        )
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()


@mcp.tool()
async def get_incident(number: str) -> dict[str, Any]:
    """Fetch one Incident by number from itsm-api."""
    client = _client()
    try:
        return await client.get_incident(number)
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
```

`number` and no other `list_incidents` argument is required, so the SDK's own pre-invocation
argument/type validation rejects a missing `number` on `get_incident`, or a non-boolean
`escalated` on `list_incidents`, before `_client()` ever runs (BEH-9).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_incident_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add mcp_server/tools/__init__.py mcp_server/tools/incidents.py mcp_server/server.py \
  tests/mcp_server/test_incident_tools.py
git commit -m "feat(mcp-server): register list_incidents and get_incident MCP tools"
```

---

### Task 4: `create_incident` tool [specialist: none]

**Charter capability:** `create_incident` tool — wraps `POST /incidents`
**Depends on:** Task 3
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `mcp_server/tools/incidents.py` — add `create_incident`
- Modify: `tests/mcp_server/test_incident_tools.py` — extend

**Tests:** `tests/mcp_server/test_incident_tools.py` (extend — BEH-4, BEH-4b, and the
schema-invalid `MCP_INPUT_INVALID` row for a missing required field; suite already created by
Task 3)

**Context to load:**
- Spec BEH-4, BEH-4b, Error Cases table (`MCP_INPUT_INVALID` row, 422 row)
- Design decision (plan header): `category`/`state` stay unconstrained `str`, `priority` stays
  unconstrained `int`, all six fields required with no defaults

- [ ] **Write failing test**

```python
# tests/mcp_server/test_incident_tools.py (append)
class _FakeCreateClient(_FakeClient):
    def __init__(self, created=None, error=None):
        super().__init__()
        self._created = created
        self._error = error

    async def create_incident(self, **kwargs):
        if self._error is not None:
            raise self._error
        return self._created


@pytest.mark.anyio
async def test_create_incident_tool_requires_all_six_fields_and_returns_created_incident(monkeypatch):
    monkeypatch.setattr(
        incidents_tools, "_client", lambda: _FakeCreateClient(created=_SAMPLE_INCIDENT)
    )

    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_incident",
            {
                "account_id": "ACCOUNT-1001", "category": "billing",
                "short_description": "Invoice mismatch",
                "description": "Customer reports a mismatch.",
                "state": "new", "priority": 2,
            },
        )

    assert result.is_error is False
    assert result.structured_content == _SAMPLE_INCIDENT


@pytest.mark.anyio
@pytest.mark.parametrize("missing_field", [
    "account_id", "category", "short_description", "description", "state", "priority",
])
async def test_create_incident_tool_missing_any_required_field_errors_before_http_request(
    monkeypatch, missing_field
):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeCreateClient()

    monkeypatch.setattr(incidents_tools, "_client", _client_spy)

    full_args = {
        "account_id": "ACCOUNT-1001", "category": "billing",
        "short_description": "Invoice mismatch", "description": "Customer reports a mismatch.",
        "state": "new", "priority": 2,
    }
    args = {k: v for k, v in full_args.items() if k != missing_field}

    async with Client(mcp) as client:
        result = await client.call_tool("create_incident", args)

    assert result.is_error is True
    assert called["value"] is False  # schema validation rejected the call before _client() ran


@pytest.mark.anyio
async def test_create_incident_tool_invalid_category_errors_with_verbatim_message(monkeypatch):
    fake = _FakeCreateClient(
        error=UpstreamError(
            422,
            "category must be one of: receiving, putaway, picking, cycle-count, billing, "
            "integrations, auth, reporting",
        )
    )
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_incident",
            {
                "account_id": "ACCOUNT-1001", "category": "not-a-real-category",
                "short_description": "x", "description": "y", "state": "new", "priority": 2,
            },
        )

    assert result.is_error is True
    assert "category must be one of" in result.content[0].text
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_incident_tools.py`
Expected: FAIL — `call_tool("create_incident", ...)` errors with an "unknown tool" result, since
`create_incident` is not registered yet.

- [ ] **Implement**

```python
# mcp_server/tools/incidents.py (append)
@mcp.tool()
async def create_incident(
    account_id: str,
    category: str,
    short_description: str,
    description: str,
    state: str,
    priority: int,
) -> dict[str, Any]:
    """Create an Incident in itsm-api. All six fields are required; state and priority have no
    default and must be supplied explicitly."""
    client = _client()
    try:
        return await client.create_incident(
            account_id=account_id, category=category, short_description=short_description,
            description=description, state=state, priority=priority,
        )
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
```

All six parameters are required with no default value — the SDK's own pre-invocation argument
validation rejects a call missing any one of them (BEH-9) before `_client()` ever runs, satisfying
BEH-4's "all six fields" requirement exactly. `category`/`state` are unconstrained `str` and
`priority` is unconstrained `int` (see plan header design decision), so an invalid domain value
(e.g. `"not-a-real-category"`) is schema-valid and reaches `itsm-api`, which returns its own
`422` — passed through verbatim by the `except UpstreamError` branch (BEH-4b).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_incident_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add mcp_server/tools/incidents.py tests/mcp_server/test_incident_tools.py
git commit -m "feat(mcp-server): register create_incident MCP tool requiring all six fields"
```

---

### Task 5: `update_incident` tool [Confirm no guard exists] [specialist: none]

> **Note on task purpose:** This task carries the plan's single highest-stakes behavior. BEH-6 and
> the charter's Non-Negotiable Principle 5 require `update_incident` to succeed unconditionally
> when resolving/closing an Incident that has an open `first_response` SLA breach or no
> customer-facing work note — with no refusal, no injected warning field, and no confirmation
> step. The Actionable Task Map explicitly calls this out: "a regression here would silently
> violate Principle 5." The test below is deliberately written so that adding *any* guard
> (a state-transition check, an SLA lookup, a confirmation prompt) would make it fail — the
> absence of such logic in the Implement step is the behavior being tested, not an oversight.

**Charter capability:** `update_incident` tool — wraps `PATCH /incidents/{number}`, unguarded
**Depends on:** Task 4
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `mcp_server/tools/incidents.py` — add `update_incident`
- Modify: `tests/mcp_server/test_incident_tools.py` — extend

**Tests:** `tests/mcp_server/test_incident_tools.py` (extend — BEH-5, BEH-6 [no-guard
regression], BEH-7, BEH-8, BEH-9; suite already extended by Task 4)

**Context to load:**
- Spec BEH-5, BEH-6, BEH-7, BEH-8, BEH-9, Postconditions ("never conditional on the resulting
  state being 'safe'")
- Constitution Non-Negotiable Principle 5; mcp-server charter Domain Model Invariant ("No McpTool
  call is refused on the grounds of what state it would produce")
- `sla-records.spec.md` BEH-7 (`business_time_only`/`has_breached` fields)

- [ ] **Write failing test**

```python
# tests/mcp_server/test_incident_tools.py (append)
class _FakeUpdateClient(_FakeClient):
    def __init__(self, updated=None, error=None):
        super().__init__()
        self._updated = updated
        self._error = error
        self.received_kwargs = None

    async def update_incident(self, number, **fields):
        self.received_kwargs = fields
        if self._error is not None:
            raise self._error
        return self._updated


@pytest.mark.anyio
async def test_update_incident_tool_updates_mutable_fields_and_returns_result(monkeypatch):
    updated = {**_SAMPLE_INCIDENT, "assigned_to": "Priya N."}
    fake = _FakeUpdateClient(updated=updated)
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "update_incident", {"number": "TICKET-004417", "assigned_to": "Priya N."}
        )

    assert result.is_error is False
    assert result.structured_content == updated
    assert fake.received_kwargs == {
        "state": None, "priority": None, "assigned_to": "Priya N.", "assignment_group": None,
    }


@pytest.mark.anyio
async def test_update_incident_tool_resolves_an_incident_with_an_open_sla_breach_unconditionally(
    monkeypatch
):
    """BEH-6 / Non-Negotiable Principle 5: this is the explicit 'confirm no guard exists' test
    from the Actionable Task Map. The Incident being resolved here carries a first_response
    TaskSla with has_breached: true and no customer-facing work note — exactly the seeded
    discrepancy #3 scenario (see incident-lifecycle.spec.md System Constitution Reference,
    Principle 6). The tool must return success with no refusal, no injected warning field, and
    no confirmation step, proving the tool layer never inspects task_sla state before calling
    itsm-api."""
    breached_incident_after_resolve = {
        **_SAMPLE_INCIDENT,
        "number": "TICKET-004480",
        "state": "resolved",
        "resolved_at": "2026-09-07T12:00:00Z",
        # Included only to document the scenario for the reader; update_incident's own response
        # shape is whatever itsm-api returns for the Incident resource — task_sla is a separate
        # entity (sla-records spec) this tool never fetches or reasons about.
    }
    fake = _FakeUpdateClient(updated=breached_incident_after_resolve)
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "update_incident", {"number": "TICKET-004480", "state": "resolved"}
        )

    # No refusal, no injected warning field, no confirmation step: the call succeeds exactly like
    # any other update, and the tool's return value is exactly what itsm-api sent back — nothing
    # added, nothing withheld.
    assert result.is_error is False
    assert result.structured_content == breached_incident_after_resolve
    assert "warning" not in result.structured_content
    assert "confirm" not in result.structured_content
    assert fake.received_kwargs["state"] == "resolved"


@pytest.mark.anyio
async def test_update_incident_tool_ignores_number_in_the_patch_body(monkeypatch):
    fake = _FakeUpdateClient(updated=_SAMPLE_INCIDENT)
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        await client.call_tool(
            "update_incident", {"number": "TICKET-004417", "state": "resolved"}
        )

    # "number" is used only to select which Incident to PATCH — it is structurally impossible
    # for it to also appear as a mutable field kwarg, satisfying the Preconditions clause.
    assert "number" not in fake.received_kwargs


@pytest.mark.anyio
async def test_update_incident_tool_unknown_number_errors_with_verbatim_message(monkeypatch):
    fake = _FakeUpdateClient(error=UpstreamError(404, "Incident TICKET-999999 not found"))
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("update_incident", {"number": "TICKET-999999", "state": "resolved"})

    assert result.is_error is True
    assert "Incident TICKET-999999 not found" in result.content[0].text


@pytest.mark.anyio
async def test_update_incident_tool_invalid_state_errors_with_verbatim_message(monkeypatch):
    fake = _FakeUpdateClient(
        error=UpstreamError(422, "state must be one of: new, in_progress, on_hold, resolved, closed")
    )
    monkeypatch.setattr(incidents_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "update_incident", {"number": "TICKET-004417", "state": "not-a-real-state"}
        )

    assert result.is_error is True
    assert "state must be one of" in result.content[0].text


@pytest.mark.anyio
async def test_update_incident_tool_missing_number_errors_before_http_request(monkeypatch):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeUpdateClient()

    monkeypatch.setattr(incidents_tools, "_client", _client_spy)

    async with Client(mcp) as client:
        result = await client.call_tool("update_incident", {"state": "resolved"})  # missing "number"

    assert result.is_error is True
    assert called["value"] is False
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_incident_tools.py`
Expected: FAIL — `call_tool("update_incident", ...)` errors with an "unknown tool" result, since
`update_incident` is not registered yet.

- [ ] **Implement**

```python
# mcp_server/tools/incidents.py (append)
@mcp.tool()
async def update_incident(
    number: str,
    state: str | None = None,
    priority: int | None = None,
    assigned_to: str | None = None,
    assignment_group: str | None = None,
) -> dict[str, Any]:
    """Update one or more mutable fields on an Incident in itsm-api.

    This call is unconditional: it carries no permission check, no state-transition guard, and no
    inspection of the Incident's SLA or work-note history. It will resolve or close an Incident
    even if its first_response SLA has breached or no customer-facing work note exists. Building
    safety around this tool is the exercise for a consuming track, not this module's job — see
    this repo's constitution Non-Negotiable Principle 5.
    """
    client = _client()
    try:
        return await client.update_incident(
            number, state=state, priority=priority,
            assigned_to=assigned_to, assignment_group=assignment_group,
        )
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
```

No branch in this function inspects `state`'s target value, looks up SLA/work-note data, or
withholds/wraps the client's return value — the function body is the same shape as
`get_incident`/`create_incident`, deliberately. Any future change that adds a conditional here
(e.g. `if state in ("resolved", "closed"): ...`) is the regression this task's BEH-6 test exists
to catch.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_incident_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add mcp_server/tools/incidents.py tests/mcp_server/test_incident_tools.py
git commit -m "feat(mcp-server): register update_incident MCP tool, unconditional per Principle 5"
```

---

### Task 6: [Regression] Confirm unreachable/5xx passthrough for all four tools [specialist: none]

> **Note on task kind:** like `mock-jira`'s analogous Task 7, this is a regression/consolidation
> task, not a greenfield TDD task — the `except UpstreamUnreachableError` branch already exists on
> every tool (added in Tasks 3-5), and `except UpstreamError` already covers any status code
> `_request()` raises for, including `5xx` (Task 1's `_request()` has no special-case that limits
> it to 4xx). There is no new production code expected here. It still runs through the same
> write-test → verify-fail → (no-op) → verify-pass checklist shape for consistency with the rest
> of this plan.

**Charter capability:** `list_incidents`, `get_incident`, `create_incident`, `update_incident`
tools (shared Error Cases rows: `MCP_UPSTREAM_ERROR` for 5xx, `MCP_UPSTREAM_UNREACHABLE`)
**Depends on:** Task 5
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `tests/mcp_server/test_incident_tools.py` — extend

**Tests:** `tests/mcp_server/test_incident_tools.py` (extend — BEH-10 and the Error Cases table's
"API unreachable"/"5xx" rows across all four tools; suite already extended by Task 5)

**Context to load:**
- Spec BEH-10, Error Cases table ("API unreachable" row, "5xx" row)
- `mock-jira/tests/mcp_server/test_issue_tools.py` Task 7 (parametrized unreachable-API pattern)

- [ ] **Write failing test**

```python
# tests/mcp_server/test_incident_tools.py (append)
_UNREACHABLE_MESSAGE = "Could not reach itsm-api at http://itsm-api: connection refused"


class _UnreachableClient(_FakeClient):
    async def list_incidents(self, **kwargs):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)

    async def get_incident(self, number):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)

    async def create_incident(self, **kwargs):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)

    async def update_incident(self, number, **fields):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)


class _FiveHundredClient(_FakeClient):
    async def list_incidents(self, **kwargs):
        raise UpstreamError(500, "Internal Server Error")

    async def get_incident(self, number):
        raise UpstreamError(500, "Internal Server Error")

    async def create_incident(self, **kwargs):
        raise UpstreamError(500, "Internal Server Error")

    async def update_incident(self, number, **fields):
        raise UpstreamError(500, "Internal Server Error")


_ALL_TOOL_CALLS = [
    ("list_incidents", {}),
    ("get_incident", {"number": "TICKET-004417"}),
    (
        "create_incident",
        {
            "account_id": "ACCOUNT-1001", "category": "billing", "short_description": "x",
            "description": "y", "state": "new", "priority": 2,
        },
    ),
    ("update_incident", {"number": "TICKET-004417", "state": "resolved"}),
]


@pytest.mark.anyio
@pytest.mark.parametrize("tool_name, arguments", _ALL_TOOL_CALLS)
async def test_incident_tool_unreachable_api_errors_with_clear_message(
    monkeypatch, tool_name, arguments
):
    monkeypatch.setattr(incidents_tools, "_client", lambda: _UnreachableClient())

    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is True
    assert "itsm-api" in result.content[0].text


@pytest.mark.anyio
@pytest.mark.parametrize("tool_name, arguments", _ALL_TOOL_CALLS)
async def test_incident_tool_5xx_errors_with_verbatim_message(monkeypatch, tool_name, arguments):
    monkeypatch.setattr(incidents_tools, "_client", lambda: _FiveHundredClient())

    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is True
    assert "Internal Server Error" in result.content[0].text
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_incident_tools.py`
Expected: this parametrized pair should already PASS if Tasks 3-5's `except UpstreamError`/
`except UpstreamUnreachableError` mapping is correct on each tool — run it in isolation *before*
Tasks 3-5 land to confirm it fails without that mapping (e.g. temporarily comment out one tool's
`except` branch) if a true red/green cycle is wanted; in this plan's intended execution order
(Tasks 3-5 already complete), this task is a confirmation, not new behavior.

- [ ] **Implement**

No implementation step is expected: the `except UpstreamError as exc: raise ToolError(exc.message)`
and `except UpstreamUnreachableError as exc: raise ToolError(str(exc))` branches already exist on
all four tools (Tasks 3-5), and neither branch special-cases status code, so a `5xx` is already
covered identically to a `4xx`. If any parametrized case unexpectedly fails, the fix belongs in
that tool's existing branch, not in new production code.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_incident_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests/mcp_server/test_incident_tools.py
git commit -m "test(mcp-server): confirm unreachable-API and 5xx passthrough for all four incident tools"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are
recorded in the validation report (`.validate.md`), not in this plan.

`governance/gates.yaml` exists and is used in place of the constitution's generic gate list:

- **Test Suite** (`test`, deterministic, required, severity error): `python3 -m pytest -q` — runs
  `tests/mcp_server/**`; this plan introduces the first tests in this repo, so no pre-existing
  suite can regress.
- **Linter** (`lint`, deterministic, required, severity error): `ruff check .` — covers every new
  `mcp_server/` and `tests/mcp_server/` file.
- **Integration Tests** (`integration-test`, deterministic, required): command is unwired
  (`command: ""` in `gates.yaml`). This gate is **skipped** for this plan; every test here runs
  against `httpx.MockTransport` or the SDK's in-memory `Client(mcp)` harness, never a live
  `itsm-api` process (which does not exist in this repo yet).
- All acceptance criteria from `incident-tools.spec.md` satisfied (BEH-1 through BEH-10).
