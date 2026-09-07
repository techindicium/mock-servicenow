<!-- partial_schema: plan@1 -->

# Implementation Plan: Work Note MCP tools (list_work_notes, add_work_note)

> **Methodology:** adev
> **Charter:** .context-index/specs/features/mcp-server/charter.md
> **Spec:** .context-index/specs/features/mcp-server/work-note-tools.spec.md
> **Review:** PASS_WITH_NOTES (2026-09-07)
> **Platform:** `mcp` Python SDK (official, PyPI `mcp`, `2.x` line — `MCPServer`/`ToolError`/
> `mcp.Client`, per the sibling `mock-jira` repo's already-verified `pip index versions mcp`
> finding for this same course cohort's toolchain), `httpx`, `anyio`, Python 3.11

**Goal:** Stand up `list_work_notes` and `add_work_note` as MCP tools that thinly wrap
`itsm-api`'s `GET /incidents/{number}/work_notes` and `POST /incidents/{number}/work_notes`,
with `add_work_note` remaining fully unguarded on `created_by`.

**Architecture:** No `mcp_server/` package exists anywhere in this repo yet (confirmed: no
`app/`, no `mcp_server/`, no `tests/` directory at all — this is a from-scratch scaffold). Four
`mcp-server` plans were authored independently against this same greenfield package
(`incident-tools`, `work-note-tools` [this plan], `escalation-and-sla-tools`, `user-tools`); to
avoid four independent copies of the same foundation colliding, `incident-tools.plan.md` is the
designated foundation owner. Its Task 1 creates `mcp_server/config.py` (`API_BASE_URL` lookup),
`mcp_server/errors.py` (`UpstreamError` / `UpstreamUnreachableError`), the base
`mcp_server/client.py` (an `httpx.AsyncClient`-backed `ItsmApiClient`, `_request()` helper
mapping 4xx/5xx/network failures onto the two typed exceptions), `requirements.txt`, `pytest.ini`,
and the `tests/mcp_server/` scaffold (`__init__.py`, `conftest.py`); its Task 3 creates
`mcp_server/server.py` (the shared `mcp = MCPServer("mock-servicenow-mcp")` instance, the
`ArgModelBase`/`extra="forbid"` strict-schema patch, and a dual-mode `main()` — `stdio` by
default, `streamable-http` on `0.0.0.0:$PORT` when `PORT` is set, mirroring `mock-jira`'s current
`mcp_server/server.py` and the charter's "streamable-http at `/mcp`") and `mcp_server/tools/
__init__.py`. This plan **extends** those files rather than recreating them: Task 1 (below) adds
`list_work_notes`/`add_work_note` methods to the existing `ItsmApiClient`, and Task 2 adds one
`import mcp_server.tools.work_notes` line to `server.py`'s existing `main()` alongside creating
`mcp_server/tools/work_notes.py` (registers the two tools, re-raising the client's typed
exceptions as `ToolError` for verbatim passthrough). Per the constitution's "HTTP contract is the
boundary" and "no inbound dependencies," nothing here imports from an `app/` package or opens the
SQLite file directly — every read/write is a real HTTP call, mocked via `httpx.MockTransport`
(client-layer tests) or the SDK's in-memory `mcp.Client(mcp)` harness (tool-layer tests), never a
live server, per "fixture-backed, offline only."

**Cross-plan dependency note:** This plan's Task 1 (`ItsmApiClient` HTTP wrapper) carries
**Depends on: incident-tools Task 1 (cross-plan)** — it modifies the `mcp_server/client.py` and
`mcp_server/errors.py` that plan's Task 1 creates, rather than creating its own copy. Task 2
(`list_work_notes` tool) additionally carries **Depends on: incident-tools Task 3 (cross-plan)**
— it modifies the `mcp_server/server.py` and `mcp_server/tools/__init__.py` that plan's Task 3
creates. `/adev:implement` must sequence `incident-tools` Tasks 1 and 3 ahead of this plan's Tasks
1 and 2 respectively.

**Review notes carried forward (PASS_WITH_NOTES, `work-note-tools.review.md`):**
- **SA-1** (warning, unaddressed in the spec text itself) — the reviewer flagged that BEH-3's
  prose lists only `incident_number`, `note_type`, and `body` as required for the happy path,
  omitting `created_by`, which is inconsistent with the wrapped `itsm-api` `work-notes.spec.md`
  BEH-3 (which requires `created_by`) and with this same spec's own BEH-4/BEH-6/BEH-7 (BEH-7's
  own error-cases example — "a missing `body`, or a non-string `created_by`" — only makes sense
  if `created_by` is itself a required, type-checked field). **This plan resolves SA-1 directly
  in code, not by editing the spec:** `add_work_note`'s tool signature declares `created_by` as a
  required `str` parameter, with no default, exactly like `incident_number`, `note_type`, and
  `body`. A call omitting `created_by` fails MCP schema validation (`MCP_INPUT_INVALID`, BEH-7)
  before any HTTP request — the same treatment as omitting `note_type` or `body`. Task 3's tests
  explicitly cover "missing `created_by`" alongside "missing `note_type`" and "missing `body`."
  This is required-**presence**, not a value restriction: BEH-4 is untouched — any string value
  of `created_by` (`customer`, an agent name, or `assist`) still succeeds unconditionally once
  the field is present, per Task 4.

**Design decision — `note_type` stays unconstrained `str` (not `Literal`):** Per BEH-6, the
tool's own schema validates only presence and type, not domain-value membership — value-level
enum checking is delegated to `itsm-api`, which returns `422` for a `note_type` outside
`comment`/`work_note`/`state_change`/`proposal_sent`. Declaring `note_type: Literal[...]` on the
tool would make an invalid value fail MCP schema validation (`MCP_INPUT_INVALID`) before ever
reaching `itsm-api`, making the reviewed `422` passthrough path (BEH-6) unreachable through this
tool — the same tension `mock-jira`'s `project-tools.plan.md` (SA-1) and `issue-tools.plan.md`
(the `issue_type`/`priority`/`status` design decision) both resolved the same way. `note_type` is
therefore a plain required `str`.

**Design decision — `created_by` carries no `Literal`/enum constraint either:** per BEH-4 and the
constitution's Principle 5, `created_by` accepts any string — `customer`, any agent name, or
`assist` — with no identity check and no value restriction of any kind. It is required
(presence-checked, see SA-1 above) but never value-constrained.

**Constitution Validation (Step 3):** Checked every task's files/behavior against `Architecture
Boundaries`. No task adds a dependency on another repo in the workspace (the new `mcp`, `httpx`,
`anyio` pip packages are dependencies of a Python package, not a workspace repo), touches auth,
adds a permission/authorship guard to `add_work_note` (which Principle 5 explicitly forbids), or
changes `itsm-api`'s documented contract — this plan only adds a *consumer*. `boundaries.yaml`
has no rules (`boundaries: []`), so no file-pattern flags apply. No task is `[REQUIRES HUMAN
APPROVAL]`.

---

## File Structure

**Create:**
- `mcp_server/tools/work_notes.py` — registers `list_work_notes` and `add_work_note` on `mcp`
- `tests/mcp_server/test_work_note_tools.py` — BEH-1 through BEH-8 coverage at the tool layer,
  using `mcp.Client(mcp)` in-memory (no subprocess, no network)

**Modify:**
- `mcp_server/client.py` — add `list_work_notes(incident_number, page=None, page_size=None)` and
  `add_work_note(incident_number, created_by, note_type, body)` to the `ItsmApiClient` class
  **created by `incident-tools.plan.md` Task 1** — this plan never recreates the file or its
  `_request()` helper
- `mcp_server/server.py` — add one `import mcp_server.tools.work_notes` line inside `main()`,
  alongside the `import mcp_server.tools.incidents` line **`incident-tools.plan.md` Task 3**
  already put there — this plan never recreates the `mcp = MCPServer(...)` instance or the
  `ArgModelBase` strict-schema patch
- `tests/mcp_server/test_client.py` — extend with `list_work_notes`/`add_work_note` coverage
  (created by `incident-tools.plan.md` Task 1)

**Reference (read, do not modify):**
- `mcp_server/config.py`, `mcp_server/errors.py`, `mcp_server/client.py`, `mcp_server/server.py`,
  `mcp_server/tools/__init__.py`, `requirements.txt`, `pytest.ini`, `tests/mcp_server/__init__.py`,
  `tests/mcp_server/conftest.py` — the shared foundation created by `incident-tools.plan.md`
  Tasks 1 and 3; this plan depends on all of these existing and extends two of them (`client.py`,
  `server.py`) per the Modify list above
- `.context-index/specs/features/itsm-api/work-notes.spec.md` — exact behavior this plan wraps:
  `GET /incidents/{number}/work_notes` (200, chronological, paginated; 404 naming the missing
  number), `POST /incidents/{number}/work_notes` (201, requires `created_by`/`note_type`/`body`,
  server-assigned `sys_id` in the `INTERACTION-NNNNNNN` scheme and `created_at`; 404 unknown
  incident; 422 invalid `note_type` or missing required field; no authorship check per BEH-4)
- `PRD.md` — `work_note` table shape (`created_by`: `customer`/agent name/`assist`; `note_type`:
  `comment`/`work_note`/`state_change`/`proposal_sent`); `GET/POST /incidents/{number}/work_notes`
  route list; "Pagination on every list endpoint."
- `.context-index/specs/features/mcp-server/charter.md` — Capability Map (`list_work_notes tool`,
  `add_work_note tool`), Domain Model (`McpTool` entity), Invariants ("input_schema validates
  before the wrapped HTTP call," "error response always carries the underlying API's error
  message verbatim," "no McpTool call is refused on the grounds of what state it would produce")
- `.context-index/specs/features/mcp-server/incident-tools.spec.md`, `incident-tools.plan.md` —
  the sibling spec/plan that owns the shared foundation this plan depends on and extends (see
  Depends On above); read to keep naming (`incident_number` argument name, `ItsmApiClient` shape)
  consistent with the already-existing `mcp_server/client.py`
- `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/client.py`,
  `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/server.py`,
  `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/errors.py`,
  `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/config.py`,
  `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/tools/issues.py` — the sibling
  repo's already-implemented, already-validated equivalents; `incident-tools.plan.md`'s foundation
  files mirror their exact shape (same `_request` helper, same `try/except UpstreamError/except
  UpstreamUnreachableError/finally: await client.aclose()` pattern, same dual-transport `main()`),
  and this plan's `add_work_note`/`list_work_notes` methods follow the same shape
- `CLAUDE.md` — constitution: "HTTP contract is the boundary," "no inbound dependencies," "MCP
  tools stay unguarded"
- `.context-index/governance/gates.yaml` — authoritative quality-gate commands (`python3 -m
  pytest -q`, `ruff check .`)

---

## Context Packets

> No `source-manifest.files[]` exists on this spec yet (greenfield — first implementation touching
> `mcp_server/` in this repo). No `orientation/architecture.md`, ADRs, or samples exist in this
> repo yet either. Context packets fall back to charter + spec + constitution + the itsm-api
> work-notes spec + PRD.md + the sibling `mock-jira` repo's already-implemented equivalents, per
> Step 2's "no source-manifest" fallback.

### Task 1 Context
- Spec: BEH-1, BEH-2, BEH-3, BEH-4, BEH-5, BEH-6, BEH-8, Error Cases table (all rows except
  `MCP_INPUT_INVALID`, which is schema-layer only)
- Charter: `charter.md` (Invariant: "error response always carries the underlying API's error
  message verbatim")
- Source files: `.context-index/specs/features/itsm-api/work-notes.spec.md` (full read — exact
  request/response shapes, `INTERACTION-NNNNNNN` sys_id scheme, 404/422 error bodies)
- Source files (from `incident-tools.plan.md` Task 1, full read — extending, not replacing):
  `mcp_server/config.py`, `mcp_server/errors.py`, `mcp_server/client.py`
- Reference: `mock-jira/mcp_server/client.py` (full read — `_request` helper pattern to mirror
  exactly)

### Task 2 Context
- Spec: BEH-1, BEH-2, BEH-7 (for `list_work_notes` only)
- Charter: `charter.md` (Capability: `list_work_notes tool`; Exposed APIs table)
- Source files (from `incident-tools.plan.md` Task 1/3, full read — extending, not replacing):
  `mcp_server/config.py`, `mcp_server/errors.py`, `mcp_server/client.py`, `mcp_server/server.py`,
  `mcp_server/tools/__init__.py`
- Reference: `mock-jira/mcp_server/tools/issues.py`, `mock-jira/mcp_server/server.py` (full read —
  the `_client()` / `@mcp.tool()` / error-mapping pattern and dual-mode `main()` already present)

### Task 3 Context
- Spec: BEH-3, BEH-7, review note SA-1 (plan header — `created_by` is required alongside
  `incident_number`/`note_type`/`body`)
- Charter: `charter.md` (Capability: `add_work_note tool`)
- Design decisions (plan header): `note_type` and `created_by` stay unconstrained `str`, both
  required, neither `Literal`-typed
- Source files (from Task 2, full read — extending): `mcp_server/tools/work_notes.py`,
  `tests/mcp_server/test_work_note_tools.py`

### Task 4 Context
- Spec: BEH-4, BEH-5, BEH-6, Postconditions ("`add_work_note`'s acceptance of any `created_by`
  value is a permanent postcondition... no later revision may narrow it without an explicit,
  human-approved amendment"), Actionable Task Map row "Confirm no author guard exists"
- Charter: `charter.md` (Business Intent — "deliberately unguarded"); System Constitution
  Reference — Principle 5
- Source files (from Task 3, full read — extending): `mcp_server/tools/work_notes.py`,
  `tests/mcp_server/test_work_note_tools.py`

### Task 5 Context
- Spec: BEH-8, Error Cases table (`MCP_UPSTREAM_UNREACHABLE` row, both tools)
- Charter: `charter.md` (Quality Attributes → Observability: "Tool errors surface the underlying
  API error message unchanged")
- Source files (from Task 1-4, full read — verifying only, no expected production-code change):
  `mcp_server/client.py`, `mcp_server/tools/work_notes.py`

---

## Parallelization

- Group A (sequential, cross-plan): `incident-tools.plan.md` Task 1 → this plan's Task 1
- Group B (sequential, cross-plan): `incident-tools.plan.md` Task 3 → this plan's Task 2 → Task 3
  → Task 4 → Task 5

This plan's Task 1 modifies `mcp_server/client.py`/`mcp_server/errors.py`, both created by
`incident-tools.plan.md` Task 1, so it cannot start before that task lands (cross-plan
dependency). This plan's Task 2 modifies `mcp_server/server.py`/`mcp_server/tools/__init__.py`,
both created by `incident-tools.plan.md` Task 3, so it additionally depends on that task. Tasks
2-5 all extend the same two files (`mcp_server/tools/work_notes.py`,
`tests/mcp_server/test_work_note_tools.py` — Task 2 creates both, the rest extend them), so there
is no file-disjoint pair anywhere in this plan's own tasks and no group can run independently of
another.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | `ItsmApiClient` HTTP wrapper (`list_work_notes`, `add_work_note`) | medium | unit | incident-tools Task 1 (cross-plan) | 0 create, 2 modify |
| 2 | `list_work_notes` tool | medium | unit | Task 1; incident-tools Task 3 (cross-plan) | 2 create, 1 modify |
| 3 | `add_work_note` tool — happy path with required `created_by` | medium | unit | Task 2 | 0 create, 2 modify |
| 4 | `add_work_note` unguarded-author regression + 404/422 passthrough | medium | unit | Task 3 | 0 create, 2 modify |
| 5 | [Regression] Confirm unreachable-API/5xx passthrough (both tools) | small | unit | Task 4 | 0 create, 1 modify |

All tasks resolve to the `unit` strategy (source: fallback — no `test_strategy` in spec
frontmatter, no `test_strategies` entries in `manifest.yaml` matching `mcp_server/**` paths). Per
Step 5, the Strategy Summary section is omitted since every task is `unit`. No
`infra_requirements:` is declared on the spec and no task needs external infrastructure — every
test in this plan runs against `httpx.MockTransport` or the SDK's own in-memory `Client(mcp)`
harness, never a live server — so the Test Infrastructure Requirements section is also omitted.

**Granularity:** `per-behavior` (source: manifest — `test_policy.granularity: per-behavior` in
`.context-index/manifest.yaml`). `tests/mcp_server/test_config.py` (foundation-level coverage) is
owned by `incident-tools.plan.md` Task 1, not this plan. `tests/mcp_server/test_client.py` is the
shared per-behavior suite for the HTTP-wrapper layer, created by `incident-tools.plan.md` Task 1
and extended here by Task 1 (BEH-1 through BEH-6, BEH-8). `tests/mcp_server/test_work_note_
tools.py` is the shared per-behavior suite for the tool layer: created by Task 2 (BEH-1, BEH-2,
BEH-7 for `list_work_notes`) and extended by Task 3 (BEH-3, BEH-7 for `add_work_note`), Task 4
(BEH-4, BEH-5, BEH-6), and Task 5 (the shared BEH-8 unreachable-API row).

---

## Task Structure

### Task 1: `ItsmApiClient` HTTP wrapper (`list_work_notes`, `add_work_note`) [specialist: none]

**Charter capability:** `list_work_notes` tool, `add_work_note` tool (HTTP-wrapper layer)
**Depends on:** `incident-tools.plan.md` Task 1 (cross-plan) — modifies the `mcp_server/client.py`
and `mcp_server/errors.py` that task creates
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `mcp_server/client.py` — add `list_work_notes`, `add_work_note` to the existing
  `ItsmApiClient` class (created by `incident-tools.plan.md` Task 1; do not recreate the file or
  its `_request()` helper)
- Test: `tests/mcp_server/test_client.py` — extend (created by `incident-tools.plan.md` Task 1)

**Tests:** `tests/mcp_server/test_client.py` (extend — first task in this plan to touch this
suite; adds coverage for BEH-1 through BEH-6 and BEH-8 at the HTTP-wrapper layer, alongside
`incident-tools`' own `list_incidents`/`get_incident`/`create_incident`/`update_incident`
coverage already in the file)

**Context to load:**
- Spec BEH-1 through BEH-6, BEH-8, Error Cases table
- `.context-index/specs/features/itsm-api/work-notes.spec.md` (full read)
- Reference: `mock-jira/mcp_server/client.py` (`_request` helper pattern to mirror exactly)

- [ ] **Write failing test**

```python
# tests/mcp_server/test_client.py
import httpx
import pytest

from mcp_server.client import ItsmApiClient
from mcp_server.errors import UpstreamError, UpstreamUnreachableError


def _client(handler) -> ItsmApiClient:
    transport = httpx.MockTransport(handler)
    return ItsmApiClient("http://itsm-api", transport=transport)


@pytest.mark.anyio
async def test_list_work_notes_returns_api_response_unmodified():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/incidents/INC0010001/work_notes"
        return httpx.Response(
            200,
            json=[{
                "sys_id": "INTERACTION-0000001", "incident_number": "INC0010001",
                "created_by": "customer", "note_type": "comment", "body": "Still broken",
                "created_at": "2026-09-05 00:00:00",
            }],
        )

    result = await _client(handler).list_work_notes("INC0010001")
    assert result[0]["sys_id"] == "INTERACTION-0000001"


@pytest.mark.anyio
async def test_list_work_notes_passes_pagination_params_as_query():
    def handler(request):
        assert request.url.params["page"] == "2"
        assert request.url.params["page_size"] == "50"
        return httpx.Response(200, json=[])

    await _client(handler).list_work_notes("INC0010001", page=2, page_size=50)


@pytest.mark.anyio
async def test_list_work_notes_unknown_incident_number_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(
            404, json={"message": "Incident INC9999999 not found", "code": "INCIDENT_NOT_FOUND"}
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).list_work_notes("INC9999999")
    assert exc_info.value.status_code == 404
    assert exc_info.value.message == "Incident INC9999999 not found"


@pytest.mark.anyio
async def test_add_work_note_returns_created_work_note_with_sys_id():
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/incidents/INC0010001/work_notes"
        import json as _json
        body = _json.loads(request.content)
        assert body == {
            "created_by": "assist", "note_type": "comment", "body": "Auto-triaged",
        }
        return httpx.Response(
            201,
            json={
                "sys_id": "INTERACTION-0000002", "incident_number": "INC0010001",
                "created_by": "assist", "note_type": "comment", "body": "Auto-triaged",
                "created_at": "2026-09-05 00:00:01",
            },
        )

    result = await _client(handler).add_work_note("INC0010001", "assist", "comment", "Auto-triaged")
    assert result["sys_id"] == "INTERACTION-0000002"
    assert result["created_by"] == "assist"


@pytest.mark.anyio
async def test_add_work_note_unknown_incident_number_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(
            404, json={"message": "Incident INC9999999 not found", "code": "INCIDENT_NOT_FOUND"}
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).add_work_note("INC9999999", "assist", "comment", "x")
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_add_work_note_invalid_note_type_raises_upstream_error_for_422():
    def handler(request):
        return httpx.Response(
            422,
            json={
                "message": "note_type must be one of: comment, work_note, state_change, "
                           "proposal_sent",
                "code": "VALIDATION_ERROR",
            },
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).add_work_note("INC0010001", "assist", "bogus", "x")
    assert exc_info.value.status_code == 422


@pytest.mark.anyio
async def test_request_maps_connection_failure_to_unreachable_error():
    def handler(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(UpstreamUnreachableError):
        await _client(handler).list_work_notes("INC0010001")


@pytest.mark.anyio
async def test_request_maps_5xx_to_upstream_error():
    def handler(request):
        return httpx.Response(500, json={"message": "Internal Server Error", "code": "INTERNAL"})

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).list_work_notes("INC0010001")
    assert exc_info.value.status_code == 500
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_client.py`
Expected: FAIL — `AttributeError: 'ItsmApiClient' object has no attribute 'list_work_notes'` (and
`'add_work_note'`), since `incident-tools.plan.md` Task 1's `ItsmApiClient` does not define these
methods yet. (This presumes `incident-tools` Task 1 has already landed — `mcp_server/client.py`
and `mcp_server/errors.py` must exist before this task's failing-test step can even import them.)

- [ ] **Implement**

```python
# mcp_server/client.py (append inside the existing ItsmApiClient class, after its Incident methods)
    async def list_work_notes(
        self, incident_number: str, page: int | None = None, page_size: int | None = None
    ) -> list[dict]:
        params: dict = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        response = await self._request(
            "GET", f"/incidents/{incident_number}/work_notes", params=params
        )
        return response.json()

    async def add_work_note(
        self, incident_number: str, created_by: str, note_type: str, body: str
    ) -> dict:
        payload = {"created_by": created_by, "note_type": note_type, "body": body}
        response = await self._request(
            "POST", f"/incidents/{incident_number}/work_notes", json=payload
        )
        return response.json()
```

Both methods reuse the `_request()` helper `incident-tools.plan.md` Task 1 already defined on
this class — no changes to `_request()` itself are needed.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_client.py`
Expected: PASS

- [ ] **Commit**

Branch (create if not already created): `feat/mcp-server/work-note-tools`

```bash
git checkout -b feat/mcp-server/work-note-tools
git add mcp_server/client.py tests/mcp_server/test_client.py
git commit -m "feat(mcp-server): add ItsmApiClient.list_work_notes and add_work_note"
```

---

### Task 2: `list_work_notes` tool [specialist: none]

**Charter capability:** `list_work_notes` tool — wraps `GET /incidents/{number}/work_notes`
**Depends on:** Task 1; `incident-tools.plan.md` Task 3 (cross-plan) — modifies the
`mcp_server/server.py` and `mcp_server/tools/__init__.py` that task creates
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `mcp_server/server.py` — add `import mcp_server.tools.work_notes` inside `main()`
  (created by `incident-tools.plan.md` Task 3; do not recreate the `mcp` instance or the
  `ArgModelBase` patch)
- Create: `mcp_server/tools/work_notes.py`
- Test: `tests/mcp_server/test_work_note_tools.py`

**Tests:** `tests/mcp_server/test_work_note_tools.py` (create — first task to touch this
behavior; covers BEH-1, BEH-2, and BEH-7 for `list_work_notes`)

**Context to load:**
- Spec BEH-1, BEH-2, BEH-7
- Charter Capability Map: `list_work_notes tool | Wraps GET /incidents/{number}/work_notes`
- Source files (from `incident-tools.plan.md` Task 3, full read — extending, not replacing):
  `mcp_server/server.py`, `mcp_server/tools/__init__.py`
- Reference: `mock-jira/mcp_server/tools/issues.py`, `mock-jira/mcp_server/server.py` (full read)

- [ ] **Write failing test**

```python
# tests/mcp_server/test_work_note_tools.py
import pytest
from mcp import Client

import mcp_server.tools.work_notes as work_notes_tools
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


class _FakeClient:
    """Stands in for ItsmApiClient — Task 2 already covers the real HTTP wiring."""

    def __init__(self, notes=None, created=None):
        self._notes = notes or []
        self._created = created

    async def list_work_notes(self, incident_number, page=None, page_size=None):
        return self._notes

    async def add_work_note(self, incident_number, created_by, note_type, body):
        return self._created

    async def aclose(self):
        pass


_SAMPLE_NOTE = {
    "sys_id": "INTERACTION-0000001", "incident_number": "INC0010001",
    "created_by": "customer", "note_type": "comment", "body": "Still broken",
    "created_at": "2026-09-05 00:00:00",
}


@pytest.mark.anyio
async def test_list_work_notes_tool_returns_api_result_unmodified(monkeypatch):
    fake = _FakeClient(notes=[_SAMPLE_NOTE])
    monkeypatch.setattr(work_notes_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_work_notes", {"incident_number": "INC0010001"})

    assert result.is_error is False
    assert result.structured_content == {"result": [_SAMPLE_NOTE]}


@pytest.mark.anyio
async def test_list_work_notes_tool_passes_pagination_params(monkeypatch):
    captured = {}

    class _CapturingClient(_FakeClient):
        async def list_work_notes(self, incident_number, page=None, page_size=None):
            captured["page"] = page
            captured["page_size"] = page_size
            return []

    monkeypatch.setattr(work_notes_tools, "_client", lambda: _CapturingClient())

    async with Client(mcp) as client:
        await client.call_tool(
            "list_work_notes", {"incident_number": "INC0010001", "page": 2, "page_size": 50}
        )

    assert captured == {"page": 2, "page_size": 50}


class _NotFoundListClient(_FakeClient):
    async def list_work_notes(self, incident_number, page=None, page_size=None):
        raise UpstreamError(404, "Incident INC9999999 not found")


@pytest.mark.anyio
async def test_list_work_notes_tool_unknown_incident_number_errors_with_verbatim_message(monkeypatch):
    monkeypatch.setattr(work_notes_tools, "_client", lambda: _NotFoundListClient())

    async with Client(mcp) as client:
        result = await client.call_tool("list_work_notes", {"incident_number": "INC9999999"})

    assert result.is_error is True
    assert "Incident INC9999999 not found" in result.content[0].text


@pytest.mark.anyio
async def test_list_work_notes_tool_missing_incident_number_errors_before_http_request(monkeypatch):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeClient()

    monkeypatch.setattr(work_notes_tools, "_client", _client_spy)

    async with Client(mcp) as client:
        result = await client.call_tool("list_work_notes", {})  # missing required incident_number

    assert result.is_error is True
    assert called["value"] is False  # schema validation rejected the call before _client() ran
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_work_note_tools.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_server.tools.work_notes'`, since that
module does not exist yet. (`mcp_server.server` and `mcp_server.tools` already exist, created by
`incident-tools.plan.md` Task 3.)

- [ ] **Implement**

```python
# mcp_server/server.py — modify main() only; do not touch the mcp instance or the ArgModelBase
# patch, both already present from incident-tools.plan.md Task 3
def main() -> None:
    import mcp_server.tools.incidents  # noqa: F401  (already present, from incident-tools)
    import mcp_server.tools.work_notes  # noqa: F401  (this plan's addition)

    from mcp_server.server import mcp as _mcp

    port = os.environ.get("PORT")
    if port:
        _mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        _mcp.run()
```

```python
# mcp_server/tools/work_notes.py
from typing import Any

from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.client import ItsmApiClient
from mcp_server.config import get_api_base_url
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


def _client() -> ItsmApiClient:
    return ItsmApiClient(get_api_base_url())


@mcp.tool()
async def list_work_notes(
    incident_number: str, page: int | None = None, page_size: int | None = None
) -> list[dict]:
    """List every WorkNote attached to an Incident in itsm-api, unmodified, in chronological
    order. Supports the same page/page_size pagination itsm-api's list endpoints accept."""
    client = _client()
    try:
        return await client.list_work_notes(incident_number, page, page_size)
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
```

`incident_number` is a required parameter — the SDK's own pre-invocation argument validation
rejects a call missing it (BEH-7) before `_client()` ever runs.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_work_note_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add mcp_server/server.py mcp_server/tools/work_notes.py tests/mcp_server/test_work_note_tools.py
git commit -m "feat(mcp-server): register list_work_notes MCP tool"
```

---

### Task 3: `add_work_note` tool — happy path with required `created_by` [specialist: none]

**Charter capability:** `add_work_note` tool — wraps `POST /incidents/{number}/work_notes`
**Depends on:** Task 2
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `mcp_server/tools/work_notes.py` — add `add_work_note`
- Modify: `tests/mcp_server/test_work_note_tools.py` — extend

**Tests:** `tests/mcp_server/test_work_note_tools.py` (extend — BEH-3 and BEH-7 for
`add_work_note`; suite already created by Task 2)

**Context to load:**
- Spec BEH-3, BEH-7, review note SA-1 (plan header)
- Design decisions (plan header): `created_by` and `note_type` are both required, unconstrained
  `str`

- [ ] **Write failing test**

```python
# tests/mcp_server/test_work_note_tools.py (append)
_CREATED_NOTE = {
    "sys_id": "INTERACTION-0000002", "incident_number": "INC0010001",
    "created_by": "assist", "note_type": "comment", "body": "Auto-triaged",
    "created_at": "2026-09-05 00:00:01",
}


class _FakeAddClient(_FakeClient):
    def __init__(self, created=None, error=None):
        super().__init__()
        self._created = created
        self._error = error
        self.received = None

    async def add_work_note(self, incident_number, created_by, note_type, body):
        self.received = (incident_number, created_by, note_type, body)
        if self._error is not None:
            raise self._error
        return self._created


@pytest.mark.anyio
async def test_add_work_note_tool_creates_and_returns_work_note_with_sys_id(monkeypatch):
    fake = _FakeAddClient(created=_CREATED_NOTE)
    monkeypatch.setattr(work_notes_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "add_work_note",
            {
                "incident_number": "INC0010001",
                "created_by": "assist",
                "note_type": "comment",
                "body": "Auto-triaged",
            },
        )

    assert result.is_error is False
    assert result.structured_content == _CREATED_NOTE
    assert fake.received == ("INC0010001", "assist", "comment", "Auto-triaged")


@pytest.mark.anyio
@pytest.mark.parametrize("missing_field", ["incident_number", "created_by", "note_type", "body"])
async def test_add_work_note_tool_missing_required_field_errors_before_http_request(
    monkeypatch, missing_field
):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeAddClient()

    monkeypatch.setattr(work_notes_tools, "_client", _client_spy)

    arguments = {
        "incident_number": "INC0010001", "created_by": "assist",
        "note_type": "comment", "body": "x",
    }
    del arguments[missing_field]

    async with Client(mcp) as client:
        result = await client.call_tool("add_work_note", arguments)

    assert result.is_error is True
    assert called["value"] is False  # schema validation rejected the call before _client() ran


@pytest.mark.anyio
async def test_add_work_note_tool_non_string_created_by_errors_before_http_request(monkeypatch):
    called = {"value": False}

    def _client_spy():
        called["value"] = True
        return _FakeAddClient()

    monkeypatch.setattr(work_notes_tools, "_client", _client_spy)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "add_work_note",
            {
                "incident_number": "INC0010001", "created_by": 12345,  # non-string
                "note_type": "comment", "body": "x",
            },
        )

    assert result.is_error is True
    assert called["value"] is False
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_work_note_tools.py`
Expected: FAIL — `call_tool("add_work_note", ...)` errors with an "unknown tool" result, since
`add_work_note` is not registered yet.

- [ ] **Implement**

```python
# mcp_server/tools/work_notes.py (append)
@mcp.tool()
async def add_work_note(
    incident_number: str,
    created_by: str,
    note_type: str,
    body: str,
) -> dict[str, Any]:
    """Add a work note to an Incident in itsm-api.

    `created_by` accepts any value — `customer`, any agent name, or `assist` — with no identity
    check; this tool performs no authorship guard by design (see this repo's constitution,
    "MCP tools stay unguarded"). `note_type` is validated for presence and type only here; its
    domain-value membership (`comment`/`work_note`/`state_change`/`proposal_sent`) is validated
    by itsm-api, which returns 422 for an invalid value. `incident_number`, `created_by`,
    `note_type`, and `body` are all required — a call missing any of them fails schema validation
    before any HTTP request is made.
    """
    client = _client()
    try:
        return await client.add_work_note(incident_number, created_by, note_type, body)
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
```

Per SA-1 (plan header), `created_by` carries no default — it is required at the same level as
`incident_number`, `note_type`, and `body`. Neither `created_by` nor `note_type` carries a
`Literal`/enum constraint (design decisions, plan header): the tool's schema checks presence and
type only, and any domain-value check is left to `itsm-api` (BEH-6) or is intentionally absent
(BEH-4).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_work_note_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add mcp_server/tools/work_notes.py tests/mcp_server/test_work_note_tools.py
git commit -m "feat(mcp-server): register add_work_note MCP tool, created_by required per SA-1"
```

---

### Task 4: `add_work_note` unguarded-author regression + 404/422 passthrough [specialist: none]

**Charter capability:** `add_work_note` tool (unguarded authorship, error passthrough)
**Depends on:** Task 3
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `tests/mcp_server/test_work_note_tools.py` — extend

**Tests:** `tests/mcp_server/test_work_note_tools.py` (extend — BEH-4, BEH-5, BEH-6; suite
already extended by Task 3)

**Context to load:**
- Spec BEH-4, BEH-5, BEH-6, Postconditions (permanence of BEH-4), Actionable Task Map row
  "Confirm no author guard exists"
- Charter: Business Intent ("deliberately unguarded"); System Constitution Reference — Principle 5

> **Note on task kind:** the `created_by` parameter added in Task 4 already carries no identity
> check by construction (there is no code path that could reject a value), so this task's "Write
> failing test" step is not expected to fail for lack of implementation — it exists to make the
> "no author guard" invariant an explicit, permanent regression test, exactly as the spec's own
> Actionable Task Map calls for ("a regression here would silently violate Principle 5"). If any
> of these tests unexpectedly fail, that is a signal someone added a guard that must be removed,
> not a signal to add one.

- [ ] **Write failing test**

```python
# tests/mcp_server/test_work_note_tools.py (append)
@pytest.mark.anyio
@pytest.mark.parametrize("author", ["customer", "jane.agent", "assist"])
async def test_add_work_note_tool_succeeds_unconditionally_for_any_created_by(monkeypatch, author):
    created = {**_CREATED_NOTE, "created_by": author}
    fake = _FakeAddClient(created=created)
    monkeypatch.setattr(work_notes_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "add_work_note",
            {
                "incident_number": "INC0010001", "created_by": author,
                "note_type": "comment", "body": "x",
            },
        )

    assert result.is_error is False
    assert fake.received == ("INC0010001", author, "comment", "x")


@pytest.mark.anyio
async def test_add_work_note_tool_unknown_incident_number_errors_with_verbatim_message(monkeypatch):
    fake = _FakeAddClient(error=UpstreamError(404, "Incident INC9999999 not found"))
    monkeypatch.setattr(work_notes_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "add_work_note",
            {
                "incident_number": "INC9999999", "created_by": "assist",
                "note_type": "comment", "body": "x",
            },
        )

    assert result.is_error is True
    assert "Incident INC9999999 not found" in result.content[0].text


@pytest.mark.anyio
async def test_add_work_note_tool_invalid_note_type_errors_with_verbatim_message(monkeypatch):
    fake = _FakeAddClient(
        error=UpstreamError(
            422,
            "note_type must be one of: comment, work_note, state_change, proposal_sent",
        )
    )
    monkeypatch.setattr(work_notes_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool(
            "add_work_note",
            {
                "incident_number": "INC0010001", "created_by": "assist",
                "note_type": "bogus", "body": "x",
            },
        )

    assert result.is_error is True
    assert "note_type must be one of" in result.content[0].text
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_work_note_tools.py`
Expected: this should already PASS given Task 4's implementation (see the "Note on task kind"
above) — run it in isolation to confirm the invariant genuinely holds end-to-end. If a true
red/green cycle is wanted, temporarily add a stub identity check to `add_work_note` and confirm
these tests catch it, then remove the stub before moving on.

- [ ] **Implement**

No implementation step is expected: `add_work_note` (Task 4) already forwards `created_by`
unconditionally and already maps `UpstreamError` to a verbatim `ToolError`. If any parametrized
case unexpectedly fails, the fix is to remove whatever guard was added, not to add new production
code.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_work_note_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests/mcp_server/test_work_note_tools.py
git commit -m "test(mcp-server): confirm add_work_note stays unguarded on created_by (Principle 5)"
```

---

### Task 5: [REGRESSION] Confirm unreachable-API/5xx passthrough for both tools [specialist: none]

> **Note on task kind:** like `mock-jira`'s equivalent consolidation tasks, this is a
> regression/consolidation task, not a greenfield TDD task — the `except UpstreamError` /
> `except UpstreamUnreachableError` branches already exist on both tools (Tasks 2-4), so no new
> production code is expected here.

**Charter capability:** `list_work_notes`, `add_work_note` tools (shared Error Cases row:
`MCP_UPSTREAM_UNREACHABLE`, and the `5xx` passthrough half of `MCP_UPSTREAM_ERROR`)
**Depends on:** Task 4
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `tests/mcp_server/test_work_note_tools.py` — extend

**Tests:** `tests/mcp_server/test_work_note_tools.py` (extend — BEH-8 across both tools; suite
already extended by Task 4)

**Context to load:**
- Spec BEH-8, Error Cases table ("API unreachable" and "API returns 5xx" rows)

- [ ] **Write failing test**

```python
# tests/mcp_server/test_work_note_tools.py (append)
_UNREACHABLE_MESSAGE = "Could not reach itsm-api at http://itsm-api: connection refused"


class _UnreachableClient(_FakeClient):
    async def list_work_notes(self, incident_number, page=None, page_size=None):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)

    async def add_work_note(self, incident_number, created_by, note_type, body):
        raise UpstreamUnreachableError(_UNREACHABLE_MESSAGE)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "tool_name, arguments",
    [
        ("list_work_notes", {"incident_number": "INC0010001"}),
        (
            "add_work_note",
            {
                "incident_number": "INC0010001", "created_by": "assist",
                "note_type": "comment", "body": "x",
            },
        ),
    ],
)
async def test_work_note_tool_unreachable_api_errors_with_clear_message(
    monkeypatch, tool_name, arguments
):
    monkeypatch.setattr(work_notes_tools, "_client", lambda: _UnreachableClient())

    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is True
    assert "itsm-api" in result.content[0].text


class _FiveHundredClient(_FakeClient):
    async def list_work_notes(self, incident_number, page=None, page_size=None):
        raise UpstreamError(500, "Internal Server Error")

    async def add_work_note(self, incident_number, created_by, note_type, body):
        raise UpstreamError(500, "Internal Server Error")


@pytest.mark.anyio
@pytest.mark.parametrize(
    "tool_name, arguments",
    [
        ("list_work_notes", {"incident_number": "INC0010001"}),
        (
            "add_work_note",
            {
                "incident_number": "INC0010001", "created_by": "assist",
                "note_type": "comment", "body": "x",
            },
        ),
    ],
)
async def test_work_note_tool_5xx_errors_with_verbatim_message(monkeypatch, tool_name, arguments):
    monkeypatch.setattr(work_notes_tools, "_client", lambda: _FiveHundredClient())

    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, arguments)

    assert result.is_error is True
    assert "Internal Server Error" in result.content[0].text
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_work_note_tools.py`
Expected: this parametrized set should already PASS if Tasks 2-4's `except UpstreamError`/`except
UpstreamUnreachableError` mapping is correct on both tools — run it in isolation to confirm both
error paths are genuinely covered end-to-end, not just at the client layer (Task 1).

- [ ] **Implement**

No implementation step is expected: the `except UpstreamError as exc: raise ToolError(exc.message)`
and `except UpstreamUnreachableError as exc: raise ToolError(str(exc))` branches already exist on
both tools (Tasks 2-4). If any parametrized case unexpectedly fails, the fix belongs in that
tool's existing branch, not in new production code.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_work_note_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests/mcp_server/test_work_note_tools.py
git commit -m "test(mcp-server): confirm unreachable-API and 5xx passthrough for both work-note tools"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are
recorded in the validation report (`.validate.md`), not in this plan.

`governance/gates.yaml` exists and is used in place of the constitution's generic gate list:

- **Test Suite** (`test`, deterministic, required, severity error): `python3 -m pytest -q` — runs
  `tests/mcp_server/**` (this plan's entire scope; no `app/` or existing `tests/` suite exists yet
  to regress).
- **Linter** (`lint`, deterministic, required, severity error): `ruff check .` — covers the new
  `mcp_server/` package in full.
- **Integration Tests** (`integration-test`, deterministic, required): command is unwired
  (`command: ""` in `gates.yaml`). This gate is **skipped** for this plan; every test here runs
  against `httpx.MockTransport` or the SDK's in-memory `Client(mcp)` harness, never a live
  `itsm-api` process.
- All acceptance criteria from `work-note-tools.spec.md` satisfied (BEH-1 through BEH-8).
