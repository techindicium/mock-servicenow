# Implementation Plan: Escalation and SLA MCP tools (list_escalations, list_sla_records)

> **Methodology:** adev
> **Charter:** .context-index/specs/features/mcp-server/charter.md
> **Spec:** .context-index/specs/features/mcp-server/escalation-and-sla-tools.spec.md
> **Review:** PASS_WITH_NOTES (2026-09-07)
> **Platform:** `mcp` Python SDK (official, PyPI `mcp`), `httpx`, Python 3.11 — new standalone process, separate from the (not-yet-built) `app/` FastAPI package

**Goal:** Stand up the `mcp_server/` package's escalation/SLA slice — `list_escalations` and
`list_sla_records` as read-only MCP tools that thinly wrap `itsm-api`'s `GET /escalations` and
`GET /sla` endpoints, passing every filter and error through unmodified.

**Architecture:** No `mcp_server/` package exists yet in this repo (greenfield — confirmed via
repo scan: only `CLAUDE.md`, `PRD.md`, `README.md`, and `.context-index/` exist on disk). Four
`mcp-server` plans were authored independently against this same greenfield package
(`incident-tools`, `work-note-tools`, `escalation-and-sla-tools` [this plan], `user-tools`); to
avoid four independent copies of the same foundation colliding, `incident-tools.plan.md` is the
designated foundation owner and this plan **extends** its output rather than laying its own base
layout. `incident-tools.plan.md` Task 1 creates `mcp_server/config.py` (`API_BASE_URL` lookup),
`mcp_server/errors.py` (`UpstreamError`/`UpstreamUnreachableError`), the base
`mcp_server/client.py` (`httpx.AsyncClient`-backed `ItsmApiClient`, `_request()` helper mapping
HTTP/network failures onto the two typed exceptions), `requirements.txt`, `pytest.ini`, and the
`tests/mcp_server/` scaffold; its Task 3 creates `mcp_server/server.py` (the shared
`mcp_server.server.mcp` instance, the `ArgModelBase`/`extra="forbid"` strict-schema patch, and
`main()`) and `mcp_server/tools/__init__.py`. This plan's tools register on that shared `mcp`
instance using the SDK's built-in argument-schema validation for BEH-5 and re-raise the client's
typed exceptions as `ToolError` so the model sees the upstream message verbatim for BEH-6. Per the
constitution's "HTTP contract is the boundary" and the charter's Domain Model invariants, this
package never imports from `app/` and never opens the SQLite file — every read is a real HTTP
call, mocked via `httpx.MockTransport` in tests (never a live server), per "fixture-backed,
offline only."

**Cross-plan dependency note:** This plan's Task 1 (`ItsmApiClient` HTTP wrapper extension)
carries **Depends on: incident-tools Task 1 (cross-plan)** — it modifies the
`mcp_server/client.py` that plan's Task 1 creates, rather than creating its own copy of
`client.py`/`errors.py`/`config.py`. Task 2 (`list_escalations` tool) additionally carries
**Depends on: incident-tools Task 3 (cross-plan)** — it modifies the `mcp_server/server.py` and
`mcp_server/tools/__init__.py` that plan's Task 3 creates. `/adev:implement` must sequence
`incident-tools` Tasks 1 and 3 ahead of this plan's Tasks 1 and 2 respectively. Test files in this
plan also move under `tests/mcp_server/` (not top-level `tests/`) to match the layout
`incident-tools.plan.md` established.

**mcp Python SDK API note:** This plan targets the same `2.x` `mcp` Python SDK API
(`mcp.server.mcpserver.MCPServer`, `mcp.server.mcpserver.exceptions.ToolError`,
`mcp.Client` for in-memory testing) that `mock-jira`'s already-implemented `mcp_server/` package
uses in this workspace — that sibling package is a working, already-verified reference for these
import paths, so this plan does not re-run an independent PyPI version check. If `/adev:implement`
finds a different `mcp` version already pinned in this repo's own `requirements.txt` (owned by
`incident-tools.plan.md` Task 1) by the time this plan executes, re-verify these import
paths against the installed version before writing code.

**Pagination parameter naming assumption:** Neither `escalations.spec.md` nor `sla-records.spec.md`
names the pagination query parameters `GET /escalations`/`GET /sla` accept, but sibling itsm-api
review notes (`work-notes.review.md`, `user-directory.spec.md`'s Error Cases table) both reference
a `page`/`page_size` convention, and `incident-lifecycle.spec.md` BEH-1 confirms every list
endpoint is paginated. This plan assumes `page: int | None` / `page_size: int | None` as the
itsm-api query parameter names. `/adev:implement` should confirm this against `itsm-api`'s actual
implementation (or OpenAPI schema, once served) before wiring Task 2's client methods; if the real
names differ, only the query-param keys in `client.py` change — no tool-facing behavior changes.

**Constitution Validation (Step 3):** Checked every task's files/behavior against `Architecture
Boundaries`. No task adds a dependency on another repo in the workspace (the `mcp`/`httpx`/`anyio`
pip packages are dependencies of a Python package, not a workspace repo), touches auth, or changes
`itsm-api`'s HTTP contract — this plan only adds a read-only *consumer* of two endpoints that
already have review-passed specs. `governance/boundaries.yaml` has `boundaries: []`, so no
file-pattern flags apply. No task is marked `[REQUIRES HUMAN APPROVAL]`.

**Review notes carried forward (PASS_WITH_NOTES, quick-synthesized-reviewer):**
- **SA-1** (warning) — *pagination-argument parity with `list_incidents`.* Resolved in this plan's
  task design rather than in the spec text: Task 2's `ItsmApiClient` methods and Task 3/4's tool
  signatures both add optional `page`/`page_size` pass-through arguments to `list_escalations` and
  `list_sla_records`, mirroring `incident-tools.spec.md` BEH-1's "pagination arguments" pass-through
  for `list_incidents`. The wrapped endpoints paginate per `escalations.spec.md`/`sla-records.spec.md`
  Actionable Task Map rows ("page params"); omitting pass-through here would silently strand a
  caller past the first page once escalation/SLA row counts grow. This is additive to the spec's
  BEH-2/BEH-4 ("any combination of the optional arguments") — `page`/`page_size` are additional
  optional arguments, not a contract change, so no spec revision is required to add them.
- **SA-2** (warning) — *`sla_definition` domain-value delegation.* Resolved in this plan's task
  design: Task 3's `list_sla_records` tool docstring and Task 3's context notes state explicitly,
  matching `incident-tools.spec.md` BEH-4b's pattern, that the tool's own input schema validates
  only presence and type for `sla_definition` (a plain `str | None`), never domain-value membership
  (`first_response`/`resolution`) — an out-of-domain value is schema-valid at the tool layer and
  reaches `itsm-api`, which rejects it with its own `422` (`VALIDATION_ERROR`), passed through
  verbatim as `MCP_UPSTREAM_ERROR` per BEH-6. Task 5 adds explicit test coverage for this exact
  path. No `Annotated[..., Field(...)]` enum constraint is added to `sla_definition` — doing so
  would make that `422` path unreachable via this tool, narrowing the reviewed contract the same
  way the sibling `project-tools.plan.md`'s SA-1 note reasoned about `key`/`name`.

---

## File Structure

**Create:**
- `mcp_server/tools/escalations.py` — registers `list_escalations` on `mcp`
- `mcp_server/tools/sla.py` — registers `list_sla_records` on `mcp`
- `tests/mcp_server/test_escalation_sla_tools.py` — BEH-1 through BEH-6 coverage at the tool
  layer, using `mcp.Client(mcp)` in-memory (no subprocess, no network)

**Modify:**
- `mcp_server/client.py` — add `list_escalations(account_id=None, open_only=None, page=None,
  page_size=None)` and `list_sla_records(incident_number=None, breached=None,
  sla_definition=None, page=None, page_size=None)` to the `ItsmApiClient` class **created by
  `incident-tools.plan.md` Task 1** — this plan never recreates the file, `errors.py`, or the
  shared `_request()` helper
- `mcp_server/server.py` — add `import mcp_server.tools.escalations` and
  `import mcp_server.tools.sla` lines inside `main()`, alongside the
  `import mcp_server.tools.incidents` line **`incident-tools.plan.md` Task 3** already put there
  — this plan never recreates the `mcp = MCPServer(...)` instance or the `ArgModelBase`
  strict-schema patch
- `tests/mcp_server/test_client.py` — extend with `list_escalations`/`list_sla_records` coverage
  (created by `incident-tools.plan.md` Task 1)

**Reference (read, do not modify):**
- `mcp_server/config.py`, `mcp_server/errors.py`, `mcp_server/client.py`, `mcp_server/server.py`,
  `mcp_server/tools/__init__.py`, `requirements.txt`, `pytest.ini`, `tests/mcp_server/__init__.py`,
  `tests/mcp_server/conftest.py` — the shared foundation created by `incident-tools.plan.md`
  Tasks 1 and 3; this plan depends on all of these existing and extends two of them (`client.py`,
  `server.py`) per the Modify list above
- `.context-index/specs/features/itsm-api/escalations.spec.md` — exact `GET /escalations` contract
  this plan wraps: filters `account_id`/`open_only`; nullable `incident_number`/`owner` serialized
  as JSON `null`, never omitted (BEH-1 through BEH-4); Error Cases table (`404`, `422`, malformed
  JSON — the last is PATCH-only, out of scope for this read-only spec)
- `.context-index/specs/features/itsm-api/sla-records.spec.md` — exact `GET /sla` contract this
  plan wraps: filters `incident_number`/`breached`/`sla_definition`; `business_time_only` field
  always present and boolean; unknown filter combination returns `200` with an empty array, never
  `404` (BEH-6); Error Cases table (`422` for invalid `sla_definition`/`breached`)
- `.context-index/specs/features/mcp-server/incident-tools.spec.md`, `incident-tools.plan.md` —
  the sibling spec/plan that owns the shared foundation this plan depends on and extends (see
  Cross-plan dependency note above); BEH-1's pagination-argument pass-through and BEH-4b's
  domain-value-delegation wording are the exact patterns SA-1/SA-2 ask this plan to mirror
- `.context-index/specs/features/mcp-server/charter.md` — Capability Map (`list_escalations tool`,
  `list_sla_records tool`), Domain Model (`McpTool` entity, Invariants: "input_schema validates
  before the wrapped HTTP call," "error response always carries the underlying API's error message
  verbatim")
- `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/client.py`,
  `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/tools/issues.py`,
  `/Users/dpavancini/Development/adev-course/mock-jira/mcp_server/server.py` — the working sibling
  implementation this plan's `client.py`/`tools/*.py`/`server.py` structure follows line-for-line
  (same workspace, same course infrastructure convention, already passing its own quality gates)
- `CLAUDE.md` — constitution: "The HTTP contract is the boundary," "Seeded discrepancies are
  load-bearing, not bugs" (Principle 6 — neither tool may filter/annotate ownerless Escalations or
  breached SLA records), "No inbound dependencies"
- `.context-index/governance/gates.yaml` — authoritative quality-gate commands

---

## Context Packets

> No `source-manifest.files[]` exists on this spec yet (greenfield — first implementation for this
> slice of `mcp-server`). No `orientation/architecture.md`, ADRs, or samples exist in this repo
> yet. Context packets fall back to charter + spec + constitution + the itsm-api specs being
> wrapped + the working `mock-jira` sibling implementation, per Step 2's "no source-manifest"
> fallback.

### Task 1 Context
- Spec: `escalation-and-sla-tools.spec.md` BEH-1 through BEH-4, BEH-6, full Error Cases table
- Source specs (full read): `escalations.spec.md` (BEH-1-4, Error Cases), `sla-records.spec.md`
  (BEH-1-6, Error Cases) — exact filter names, nullable-field serialization, empty-array-not-404
  behavior (sla-records BEH-6)
- Charter: `charter.md` (Invariants: "A tool call's error response always carries the underlying
  API's error message verbatim")
- Source files (from `incident-tools.plan.md` Task 1, full read — extending, not replacing):
  `mcp_server/client.py`, `mcp_server/errors.py`
- Reference: `mock-jira/mcp_server/client.py`, `mock-jira/mcp_server/errors.py` (full read — exact
  pattern: `_request()` helper, `UpstreamError`/`UpstreamUnreachableError` mapping)
- Plan header: pagination parameter naming assumption (`page`/`page_size`)

### Task 2 Context
- Spec: `escalation-and-sla-tools.spec.md` BEH-1, BEH-2
- Charter: `charter.md` (Capability: `list_escalations tool`; Exposed APIs table)
- Plan header: SA-1 note (pagination pass-through)
- Source files (from Task 1, full read): `mcp_server/client.py`
- Source files (from `incident-tools.plan.md` Task 1/3, full read — extending, not replacing):
  `mcp_server/config.py`, `mcp_server/server.py`, `mcp_server/tools/__init__.py`
- Reference: `mock-jira/mcp_server/tools/issues.py`, `mock-jira/mcp_server/server.py` (full read —
  `@mcp.tool()` registration pattern, `_client()` helper, `main()` entrypoint shape already
  present)

### Task 3 Context
- Spec: `escalation-and-sla-tools.spec.md` BEH-3, BEH-4
- Charter: `charter.md` (Capability: `list_sla_records tool`)
- Plan header: SA-1 note (pagination pass-through), SA-2 note (`sla_definition` domain-value
  delegation — exact wording to mirror from `incident-tools.spec.md` BEH-4b)
- Source files (from Task 2, full read — extending, not replacing):
  `mcp_server/tools/escalations.py` (sibling pattern in the same package), `mcp_server/server.py`
- Source files (from Task 1, full read): `mcp_server/client.py`

### Task 4 Context
- Spec: `escalation-and-sla-tools.spec.md` BEH-5, Error Cases table (`MCP_INPUT_INVALID` row)
- Charter: `charter.md` (Invariants: "Every McpTool's input_schema validates before the wrapped
  HTTP call is made — a request the schema rejects never reaches itsm-api")
- Source files (from Task 2/3, full read — verifying only, no expected production change):
  `mcp_server/tools/escalations.py`, `mcp_server/tools/sla.py`

### Task 5 Context
- Spec: `escalation-and-sla-tools.spec.md` BEH-6, full Error Cases table (`422`/`5xx`/unreachable
  rows)
- Charter: `charter.md` (Quality Attributes → Observability: "Tool errors surface the underlying
  API error message unchanged")
- Source files (from Task 1/2/3, full read — verifying only): `mcp_server/client.py`,
  `mcp_server/tools/escalations.py`, `mcp_server/tools/sla.py`

---

## Parallelization

- Group A (sequential, cross-plan): `incident-tools.plan.md` Task 1 → this plan's Task 1
- Group B (sequential, cross-plan): `incident-tools.plan.md` Task 3 → this plan's Task 2 → Task 3
  → Task 4 → Task 5

This plan's Task 1 modifies `mcp_server/client.py`/`mcp_server/errors.py`, both created by
`incident-tools.plan.md` Task 1, so it cannot start before that task lands (cross-plan
dependency). This plan's Task 2 modifies `mcp_server/server.py`/`mcp_server/tools/__init__.py`,
both created by `incident-tools.plan.md` Task 3, so it additionally depends on that task. Task 2
(`mcp_server/tools/escalations.py`, first cut) imports both `mcp_server.config.get_api_base_url`
and `mcp_server.client.ItsmApiClient`. Tasks 2 → 3 → 4 → 5 are then strictly sequential — each
extends the same shared test suite (`tests/mcp_server/test_escalation_sla_tools.py`), and Task 3
additionally shares `mcp_server/server.py` with Task 2.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | `ItsmApiClient` HTTP wrapper (escalations + SLA) | medium | unit | incident-tools Task 1 (cross-plan) | 0 create, 2 modify |
| 2 | `list_escalations` tool (BEH-1, BEH-2) | small | unit | Task 1; incident-tools Task 3 (cross-plan) | 2 create, 1 modify |
| 3 | `list_sla_records` tool (BEH-3, BEH-4) | medium | unit | Task 2 | 1 create, 1 modify |
| 4 | Schema-invalid input rejected before HTTP call (BEH-5) | small | unit | Task 3 | 0 create, 1 modify |
| 5 | Upstream error + unreachable-API passthrough (BEH-6) | small | unit | Task 4 | 0 create, 1 modify |

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
and extended here by Task 1. `tests/mcp_server/test_escalation_sla_tools.py` is the shared
per-behavior suite for the tool layer: created once by Task 2 (BEH-1, BEH-2) and extended by
Task 3 (BEH-3, BEH-4), Task 4 (BEH-5), and Task 5 (BEH-6).

---

## Task Structure

### Task 1: `ItsmApiClient` HTTP wrapper (escalations + SLA) [specialist: none]

**Charter capability:** Shared HTTP wiring for `list_escalations`/`list_sla_records` tools
**Depends on:** `incident-tools.plan.md` Task 1 (cross-plan) — modifies the `mcp_server/client.py`
that task creates
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `mcp_server/client.py` — add `list_escalations`, `list_sla_records`, and
  `_filtered_params` to the existing `ItsmApiClient` class (created by `incident-tools.plan.md`
  Task 1; do not recreate the file, `errors.py`, or the shared `_request()` helper)
- Test: `tests/mcp_server/test_client.py` — extend (created by `incident-tools.plan.md` Task 1)

**Tests:** `tests/mcp_server/test_client.py` (extend — first task in this plan to touch this
suite; adds coverage for BEH-1 through BEH-4 and BEH-6 at the HTTP-wrapper layer, alongside
`incident-tools`' own coverage already in the file)

**Context to load:**
- Spec BEH-1 through BEH-4, BEH-6, full Error Cases table
- `escalations.spec.md` BEH-1-4 (query params, nullable-field serialization)
- `sla-records.spec.md` BEH-1-6 (query params, `business_time_only`, empty-array-not-404)
- Source files (from `incident-tools.plan.md` Task 1, full read — extending, not replacing):
  `mcp_server/client.py`, `mcp_server/errors.py`
- Reference: `mock-jira/mcp_server/client.py`, `mock-jira/mcp_server/errors.py` (exact pattern)
- Plan header: pagination parameter naming assumption (`page`/`page_size`)

- [ ] **Write failing test**

`incident-tools.plan.md` Task 1 already defines a `_client(handler)` helper and the
`httpx`/`pytest`/`ItsmApiClient`/`UpstreamError`/`UpstreamUnreachableError` imports at the top of
`tests/mcp_server/test_client.py` — reuse them; do not redefine.

```python
# tests/mcp_server/test_client.py (append)


@pytest.mark.anyio
async def test_list_escalations_no_args_returns_result_unmodified_including_ownerless():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/escalations"
        assert request.url.params == httpx.QueryParams()
        return httpx.Response(
            200,
            json=[
                {"number": "ESCALATION-0001", "account_id": "ACC-1", "owner": None, "closed_at": None},
            ],
        )

    result = await _client(handler).list_escalations()
    assert result[0]["owner"] is None


@pytest.mark.anyio
async def test_list_escalations_forwards_account_id_open_only_and_pagination():
    def handler(request):
        assert dict(request.url.params) == {
            "account_id": "ACC-1",
            "open_only": "true",
            "page": "2",
            "page_size": "50",
        }
        return httpx.Response(200, json=[])

    await _client(handler).list_escalations(
        account_id="ACC-1", open_only=True, page=2, page_size=50
    )


@pytest.mark.anyio
async def test_list_sla_records_no_args_returns_result_unmodified_including_breached():
    def handler(request):
        assert request.url.path == "/sla"
        assert request.url.params == httpx.QueryParams()
        return httpx.Response(
            200,
            json=[{"incident_number": "TICKET-000001", "sla_definition": "resolution", "has_breached": True}],
        )

    result = await _client(handler).list_sla_records()
    assert result[0]["has_breached"] is True


@pytest.mark.anyio
async def test_list_sla_records_forwards_all_filters_and_pagination():
    def handler(request):
        assert dict(request.url.params) == {
            "incident_number": "TICKET-000001",
            "breached": "false",
            "sla_definition": "first_response",
            "page": "1",
            "page_size": "25",
        }
        return httpx.Response(200, json=[])

    await _client(handler).list_sla_records(
        incident_number="TICKET-000001",
        breached=False,
        sla_definition="first_response",
        page=1,
        page_size=25,
    )


@pytest.mark.anyio
async def test_list_sla_records_invalid_sla_definition_raises_upstream_error_verbatim():
    def handler(request):
        return httpx.Response(
            422,
            json={
                "message": "sla_definition must be one of: first_response, resolution",
                "code": "VALIDATION_ERROR",
            },
        )

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).list_sla_records(sla_definition="bogus")
    assert exc_info.value.status_code == 422
    assert "first_response, resolution" in exc_info.value.message


@pytest.mark.anyio
async def test_list_escalations_unreachable_api_raises_upstream_unreachable_error():
    def handler(request):
        raise httpx.ConnectError("Connection refused", request=request)

    with pytest.raises(UpstreamUnreachableError):
        await _client(handler).list_escalations()


@pytest.mark.anyio
async def test_list_sla_records_5xx_raises_upstream_error_with_body_verbatim():
    def handler(request):
        return httpx.Response(500, json={"message": "internal error", "code": "INTERNAL_ERROR"})

    with pytest.raises(UpstreamError) as exc_info:
        await _client(handler).list_sla_records()
    assert exc_info.value.status_code == 500
    assert exc_info.value.message == "internal error"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_client.py`
Expected: FAIL — `AttributeError: 'ItsmApiClient' object has no attribute 'list_escalations'`
(and `'list_sla_records'`), since `incident-tools.plan.md` Task 1's `ItsmApiClient` does not
define these methods yet. (This presumes `incident-tools` Task 1 has already landed —
`mcp_server/client.py` and `mcp_server/errors.py` must exist before this task's failing-test step
can even import them.)

- [ ] **Implement**

```python
# mcp_server/client.py (append inside the existing ItsmApiClient class, after its Incident
# methods; the class already imports UpstreamError/UpstreamUnreachableError and defines
# _request() — reuse both, do not redefine)
    async def list_escalations(
        self,
        account_id: str | None = None,
        open_only: bool | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> list[dict]:
        params = self._filtered_params(
            account_id=account_id, open_only=open_only, page=page, page_size=page_size
        )
        response = await self._request("GET", "/escalations", params=params)
        return response.json()

    async def list_sla_records(
        self,
        incident_number: str | None = None,
        breached: bool | None = None,
        sla_definition: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> list[dict]:
        params = self._filtered_params(
            incident_number=incident_number,
            breached=breached,
            sla_definition=sla_definition,
            page=page,
            page_size=page_size,
        )
        response = await self._request("GET", "/sla", params=params)
        return response.json()

    @staticmethod
    def _filtered_params(**kwargs) -> dict:
        return {key: value for key, value in kwargs.items() if value is not None}
```

`httpx.MockTransport` intercepts every request in-process — no live server, no real network,
consistent with the constitution's "fixture-backed, offline only" principle. Both new methods
reuse the `_request()` helper `incident-tools.plan.md` Task 1 already defined on this class — no
changes to `_request()` itself are needed. `_filtered_params` drops `None` values so BEH-1/BEH-3's
"no query parameters" case sends an empty query string, and `httpx` serializes `bool`/`int`
values as their string forms (`True` → `"true"`) matching the test's assertions above.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_client.py`
Expected: PASS

- [ ] **Commit**

Branch (create if not already created): `feat/mcp-server/escalation-and-sla-tools`

```bash
git checkout -b feat/mcp-server/escalation-and-sla-tools
git add mcp_server/client.py tests/mcp_server/test_client.py
git commit -m "feat(mcp-server): add ItsmApiClient HTTP wrapper for escalations and SLA endpoints"
```

---

### Task 2: `list_escalations` tool (BEH-1, BEH-2) [specialist: none]

**Charter capability:** `list_escalations tool` — wraps `GET /escalations`
**Depends on:** Task 1; `incident-tools.plan.md` Task 3 (cross-plan) — modifies the
`mcp_server/server.py` and `mcp_server/tools/__init__.py` that task creates
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `mcp_server/server.py` — add `import mcp_server.tools.escalations` and
  `import mcp_server.tools.sla` inside `main()` (created by `incident-tools.plan.md` Task 3; do
  not recreate the `mcp` instance or the `ArgModelBase` patch)
- Create: `mcp_server/tools/escalations.py`
- Test: `tests/mcp_server/test_escalation_sla_tools.py`

**Tests:** `tests/mcp_server/test_escalation_sla_tools.py` (create — first task to touch this
behavior; covers BEH-1, BEH-2)

**Context to load:**
- Spec BEH-1, BEH-2
- Charter Capability Map: `list_escalations tool | Wraps GET /escalations, filter parameters`
- Plan header SA-1 note (pagination pass-through)
- Source files (from Task 1, full read): `mcp_server/client.py`
- Source files (from `incident-tools.plan.md` Task 1/3, full read — extending, not replacing):
  `mcp_server/config.py`, `mcp_server/server.py`, `mcp_server/tools/__init__.py`

- [ ] **Write failing test**

```python
# tests/mcp_server/test_escalation_sla_tools.py
import pytest
from mcp import Client

import mcp_server.tools.escalations as escalations_tools
from mcp_server.server import mcp


class _FakeClient:
    """Stands in for ItsmApiClient — Task 1 already covers the real HTTP wiring."""

    def __init__(self, escalations=None, sla_records=None, error=None):
        self._escalations = escalations or []
        self._sla_records = sla_records or []
        self._error = error
        self.last_escalation_call = None
        self.last_sla_call = None

    async def list_escalations(self, account_id=None, open_only=None, page=None, page_size=None):
        self.last_escalation_call = dict(
            account_id=account_id, open_only=open_only, page=page, page_size=page_size
        )
        if self._error is not None:
            raise self._error
        return self._escalations

    async def list_sla_records(
        self, incident_number=None, breached=None, sla_definition=None, page=None, page_size=None
    ):
        self.last_sla_call = dict(
            incident_number=incident_number,
            breached=breached,
            sla_definition=sla_definition,
            page=page,
            page_size=page_size,
        )
        if self._error is not None:
            raise self._error
        return self._sla_records

    async def aclose(self):
        pass


@pytest.mark.anyio
async def test_list_escalations_tool_no_args_returns_full_result_including_ownerless(monkeypatch):
    fake = _FakeClient(
        escalations=[
            {"number": "ESCALATION-0001", "account_id": "ACC-1", "owner": None, "closed_at": None}
        ]
    )
    monkeypatch.setattr(escalations_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_escalations", {})

    assert result.is_error is False
    assert fake.last_escalation_call == dict(
        account_id=None, open_only=None, page=None, page_size=None
    )
    # A bare `list` return is not itself a JSON object, so the SDK wraps it under a "result" key
    # for structured_content. Confirm this exact shape against the installed SDK version during
    # implementation; if it differs, this is the one assertion to adjust.
    assert result.structured_content == {"result": fake._escalations}
    assert result.structured_content["result"][0]["owner"] is None
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_escalation_sla_tools.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'mcp_server.tools.escalations'`, since that
module does not exist yet. (`mcp_server.server` and `mcp_server.tools` already exist, created by
`incident-tools.plan.md` Task 3.)

- [ ] **Implement**

```python
# mcp_server/server.py — modify main() only; do not touch the mcp instance or the ArgModelBase
# patch, both already present from incident-tools.plan.md Task 3
def main() -> None:
    import mcp_server.tools.incidents  # noqa: F401  (already present, from incident-tools)
    import mcp_server.tools.escalations  # noqa: F401  (this task's addition)

    from mcp_server.server import mcp as _mcp

    port = os.environ.get("PORT")
    if port:
        _mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        _mcp.run()
```

```python
# mcp_server/tools/escalations.py
from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.client import ItsmApiClient
from mcp_server.config import get_api_base_url
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


def _client() -> ItsmApiClient:
    return ItsmApiClient(get_api_base_url())


@mcp.tool()
async def list_escalations(
    account_id: str | None = None,
    open_only: bool | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> list[dict]:
    """List Escalations known to itsm-api.

    With no arguments, returns the full unfiltered result, including any Escalation whose
    `owner` is null — this tool never filters, flags, or annotates ownerless Escalations.
    `page`/`page_size` pass through to GET /escalations pagination, mirroring `list_incidents`.
    """
    client = _client()
    try:
        return await client.list_escalations(account_id, open_only, page, page_size)
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
```

`mcp_server/tools/__init__.py` already exists (created by `incident-tools.plan.md` Task 3).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_escalation_sla_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add mcp_server/server.py mcp_server/tools/escalations.py tests/mcp_server/test_escalation_sla_tools.py
git commit -m "feat(mcp-server): register list_escalations MCP tool"
```

---

### Task 3: `list_sla_records` tool (BEH-3, BEH-4) [specialist: none]

**Charter capability:** `list_sla_records tool` — wraps `GET /sla`
**Depends on:** Task 2
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `mcp_server/server.py` — add `import mcp_server.tools.sla` inside `main()`
- Create: `mcp_server/tools/sla.py`
- Modify: `tests/mcp_server/test_escalation_sla_tools.py` — extend

**Tests:** `tests/mcp_server/test_escalation_sla_tools.py` (extend — BEH-3, BEH-4; suite already
created by Task 2)

**Context to load:**
- Spec BEH-3, BEH-4
- Plan header SA-1 note (pagination pass-through), SA-2 note (`sla_definition` domain-value
  delegation — mirror `incident-tools.spec.md` BEH-4b's wording)
- `mcp_server/tools/escalations.py` (from Task 2, full read — sibling pattern)

- [ ] **Write failing test**

```python
# tests/mcp_server/test_escalation_sla_tools.py (append)
import mcp_server.tools.sla as sla_tools


@pytest.mark.anyio
async def test_list_sla_records_tool_no_args_returns_full_result_including_breached(monkeypatch):
    fake = _FakeClient(
        sla_records=[
            {"incident_number": "TICKET-000001", "sla_definition": "resolution", "has_breached": True}
        ]
    )
    monkeypatch.setattr(sla_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_sla_records", {})

    assert result.is_error is False
    assert fake.last_sla_call == dict(
        incident_number=None, breached=None, sla_definition=None, page=None, page_size=None
    )
    assert result.structured_content == {"result": fake._sla_records}
    assert result.structured_content["result"][0]["has_breached"] is True


@pytest.mark.anyio
async def test_list_sla_records_tool_forwards_all_filters_and_pagination(monkeypatch):
    fake = _FakeClient(sla_records=[])
    monkeypatch.setattr(sla_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        await client.call_tool(
            "list_sla_records",
            {
                "incident_number": "TICKET-000001",
                "breached": False,
                "sla_definition": "first_response",
                "page": 1,
                "page_size": 25,
            },
        )

    assert fake.last_sla_call == dict(
        incident_number="TICKET-000001",
        breached=False,
        sla_definition="first_response",
        page=1,
        page_size=25,
    )


@pytest.mark.anyio
async def test_list_escalations_tool_forwards_account_id_open_only_and_pagination(monkeypatch):
    fake = _FakeClient(escalations=[])
    monkeypatch.setattr(escalations_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        await client.call_tool(
            "list_escalations",
            {"account_id": "ACC-1", "open_only": True, "page": 2, "page_size": 50},
        )

    assert fake.last_escalation_call == dict(
        account_id="ACC-1", open_only=True, page=2, page_size=50
    )
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_escalation_sla_tools.py`
Expected: FAIL — `call_tool("list_sla_records", ...)` errors with an "unknown tool" result, since
`list_sla_records` is not registered yet.

- [ ] **Implement**

```python
# mcp_server/server.py — modify main() only; add the sla import alongside the escalations one
# Task 2 already added
def main() -> None:
    import mcp_server.tools.incidents  # noqa: F401  (already present, from incident-tools)
    import mcp_server.tools.escalations  # noqa: F401  (already present, from Task 2)
    import mcp_server.tools.sla  # noqa: F401  (this task's addition)

    from mcp_server.server import mcp as _mcp

    port = os.environ.get("PORT")
    if port:
        _mcp.run(transport="streamable-http", host="0.0.0.0", port=int(port))
    else:
        _mcp.run()
```

```python
# mcp_server/tools/sla.py
from mcp.server.mcpserver.exceptions import ToolError

from mcp_server.client import ItsmApiClient
from mcp_server.config import get_api_base_url
from mcp_server.errors import UpstreamError, UpstreamUnreachableError
from mcp_server.server import mcp


def _client() -> ItsmApiClient:
    return ItsmApiClient(get_api_base_url())


@mcp.tool()
async def list_sla_records(
    incident_number: str | None = None,
    breached: bool | None = None,
    sla_definition: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> list[dict]:
    """List TaskSla records known to itsm-api.

    With no arguments, returns the full unfiltered result, including any record where
    `has_breached` is true — this tool never filters, flags, or annotates breached SLA records.
    `sla_definition`'s value-domain (`first_response`/`resolution`) is not validated by this
    tool's own schema — only presence and type are checked here. An out-of-domain value is
    schema-valid and reaches itsm-api, which rejects it with its own 422, passed through verbatim.
    `page`/`page_size` pass through to GET /sla pagination, mirroring `list_incidents`.
    """
    client = _client()
    try:
        return await client.list_sla_records(incident_number, breached, sla_definition, page, page_size)
    except UpstreamError as exc:
        raise ToolError(exc.message) from exc
    except UpstreamUnreachableError as exc:
        raise ToolError(str(exc)) from exc
    finally:
        await client.aclose()
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_escalation_sla_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add mcp_server/server.py mcp_server/tools/sla.py tests/mcp_server/test_escalation_sla_tools.py
git commit -m "feat(mcp-server): register list_sla_records MCP tool with pagination pass-through"
```

---

### Task 4: Schema-invalid input rejected before HTTP call (BEH-5) [specialist: none]

**Charter capability:** `list_escalations tool`, `list_sla_records tool` (BEH-5, shared across
both)
**Depends on:** Task 3
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `tests/mcp_server/test_escalation_sla_tools.py` — extend

**Tests:** `tests/mcp_server/test_escalation_sla_tools.py` (extend — BEH-5; suite already created
by Task 2)

**Context to load:**
- Spec BEH-5: "When either tool in this spec is invoked with input that fails its declared input
  schema (e.g. a non-boolean `open_only` or `breached`), then the tool call errors before any HTTP
  request is made."
- Charter Invariant: "Every McpTool's input_schema validates before the wrapped HTTP call is made"

- [ ] **Write failing test**

```python
# tests/mcp_server/test_escalation_sla_tools.py (append)
@pytest.mark.anyio
async def test_list_escalations_tool_non_boolean_open_only_errors_before_http_call(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(escalations_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_escalations", {"open_only": "not-a-bool"})

    assert result.is_error is True
    assert fake.last_escalation_call is None  # schema validation rejected the call before _client() ran


@pytest.mark.anyio
async def test_list_sla_records_tool_non_boolean_breached_errors_before_http_call(monkeypatch):
    fake = _FakeClient()
    monkeypatch.setattr(sla_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_sla_records", {"breached": "not-a-bool"})

    assert result.is_error is True
    assert fake.last_sla_call is None
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_escalation_sla_tools.py`
Expected: this pair should already PASS if the SDK's declared-type argument validation
(`open_only: bool | None`, `breached: bool | None`) rejects a non-boolean string before dispatch —
run it in isolation first to confirm a true red/green cycle: if it unexpectedly passes without any
implementation change, that confirms Tasks 2/3's plain-`bool` type hints already satisfy BEH-5
(the SDK generates the input schema from the function signature), and this task is a confirmation
task rather than new production behavior, matching the sibling `project-tools.plan.md`'s
missing-required-field test pattern.

- [ ] **Implement**

No implementation step is expected: `mcp.server.mcpserver`'s `@mcp.tool()` decorator derives each
tool's JSON-schema input validation from its Python type hints, and Tasks 2/3 already declared
`open_only: bool | None` / `breached: bool | None`. If this test unexpectedly fails, the fix is to
confirm the installed SDK version performs pre-invocation type coercion/rejection consistent with
its declared schema (per the mcp Python SDK API note in the plan header) — not to add manual
validation code in the tool bodies, which would duplicate what the schema already enforces.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_escalation_sla_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests/mcp_server/test_escalation_sla_tools.py
git commit -m "test(mcp-server): confirm schema-invalid input is rejected before any HTTP call"
```

---

### Task 5: Upstream error + unreachable-API passthrough (BEH-6) [specialist: none]

**Charter capability:** `list_escalations tool`, `list_sla_records tool` (BEH-6, shared across
both)
**Depends on:** Task 4
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `tests/mcp_server/test_escalation_sla_tools.py` — extend

**Tests:** `tests/mcp_server/test_escalation_sla_tools.py` (extend — BEH-6; suite already created
by Task 2)

**Context to load:**
- Spec BEH-6: "When itsm-api is unreachable, or returns a 5xx response, for either tool in this
  spec, then the tool call errors with a message naming the failure — connection failure or the
  API's 5xx body passed through verbatim, whichever occurred."
- Plan header SA-2 note: also confirm the `422` invalid-`sla_definition` path (Error Cases table)
  passes through verbatim at the tool layer, closing the loop the client-layer test in Task 1
  already opened at the HTTP-wrapper layer.

- [ ] **Write failing test**

```python
# tests/mcp_server/test_escalation_sla_tools.py (append)
from mcp_server.errors import UpstreamError, UpstreamUnreachableError

_UNREACHABLE_MESSAGE = "Could not reach itsm-api at http://itsm-api: connection refused"


@pytest.mark.anyio
async def test_list_escalations_tool_unreachable_api_errors_with_clear_message(monkeypatch):
    fake = _FakeClient(error=UpstreamUnreachableError(_UNREACHABLE_MESSAGE))
    monkeypatch.setattr(escalations_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_escalations", {})

    assert result.is_error is True
    assert "itsm-api" in result.content[0].text


@pytest.mark.anyio
async def test_list_sla_records_tool_5xx_errors_with_body_verbatim(monkeypatch):
    fake = _FakeClient(error=UpstreamError(500, "internal error"))
    monkeypatch.setattr(sla_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        result = await client.call_tool("list_sla_records", {})

    assert result.is_error is True
    assert "internal error" in result.content[0].text


@pytest.mark.anyio
async def test_list_sla_records_tool_invalid_sla_definition_errors_with_422_message_verbatim(monkeypatch):
    fake = _FakeClient(
        error=UpstreamError(422, "sla_definition must be one of: first_response, resolution")
    )
    monkeypatch.setattr(sla_tools, "_client", lambda: fake)

    async with Client(mcp) as client:
        # Note: "bogus" is a syntactically valid str, so this reaches the (faked) HTTP call rather
        # than failing schema validation — see SA-2 in the plan header.
        result = await client.call_tool("list_sla_records", {"sla_definition": "bogus"})

    assert result.is_error is True
    assert "first_response, resolution" in result.content[0].text
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/mcp_server/test_escalation_sla_tools.py`
Expected: this set should already PASS if Tasks 2/3's `except UpstreamError`/`except
UpstreamUnreachableError` mapping is correct — run it in isolation *before* Tasks 2/3 land to
confirm a true red/green cycle (e.g. temporarily comment out the `except` branches) if desired; in
this plan's intended execution order (Tasks 2 and 3 already complete), this task is a
confirmation, not new behavior.

- [ ] **Implement**

No implementation step is expected: the `except UpstreamError as exc: raise ToolError(exc.message)`
and `except UpstreamUnreachableError as exc: raise ToolError(str(exc))` branches already exist in
both `list_escalations` and `list_sla_records` (Tasks 2 and 3). If this test unexpectedly fails,
the fix belongs in one of those existing branches, not in new production code.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/mcp_server/test_escalation_sla_tools.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests/mcp_server/test_escalation_sla_tools.py
git commit -m "test(mcp-server): confirm upstream error and unreachable-API passthrough for escalation/SLA tools"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are
recorded in the validation report (`.validate.md`), not in this plan.

`.context-index/governance/gates.yaml` exists and is used in place of the constitution's generic
gate list:

- **Test Suite** (`test`, deterministic, required, severity error): `python3 -m pytest -q` — runs
  `tests/**` including the new files this plan adds.
- **Linter** (`lint`, deterministic, required, severity error): `ruff check .` — covers the new
  `mcp_server/` package.
- **Integration Tests** (`integration-test`, deterministic, required): command is unwired
  (`command: ""` in `gates.yaml`). This gate is **skipped** for this plan; every test here runs
  against `httpx.MockTransport` or the SDK's in-memory `Client(mcp)` harness, never a live
  `itsm-api` process.
- All acceptance criteria from `escalation-and-sla-tools.spec.md` satisfied (BEH-1 through BEH-6).
