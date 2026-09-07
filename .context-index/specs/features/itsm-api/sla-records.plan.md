<!-- partial_schema: plan@1 -->

# Implementation Plan: Task SLA record listing

> **Methodology:** adev
> **Charter:** .context-index/specs/features/itsm-api/charter.md
> **Spec:** .context-index/specs/features/itsm-api/sla-records.spec.md
> **Review:** PASS_WITH_NOTES (2026-09-07)
> **Platform:** FastAPI (net new), Python 3.11, SQLite, Pydantic — no framework/ORM currently
> installed anywhere in this repo

**Goal:** Implement the read-only `GET /sla` endpoint — listing Task SLA attainment records,
filterable by `incident_number`/`breached`/`sla_definition`, paginated — as the first HTTP surface
in this repo.

**Architecture:** Per a cross-plan consistency pass (2026-09-07), `incident-lifecycle.plan.md`'s
Task 1 is this charter's designated canonical foundation owner: it creates `app/db.py` (with
`create_schema()` already covering **all six** charter tables, including `task_sla`),
`app/models.py`, `app/errors.py`, `app/main.py`, `app/pagination.py`, `requirements.txt`, and
`tests/conftest.py` (the `client`/`conn` fixtures). This plan's Task 1 **depends on** that
foundation and **extends** `app/models.py` with this spec's own `TaskSlaRead`/`PaginatedTaskSla`
models — it does not recreate the `task_sla` table in `create_schema()` (already defined there) or
any of the other shared files. `task_sla` is defined **without** an enforced `incident_number`
foreign key (matching `incident-lifecycle`'s own `create_schema()` statement for `task_sla`, which
likewise omits the FK): the spec's own Precondition states TaskSla rows reference Incidents at the
data-modeling level, but BEH-6 explicitly requires `GET /sla` to return an empty paginated page —
never a 404 or FK error — for an `incident_number` matching no rows, so no runtime existence check
against an `incidents` table is part of this contract.

**Constitution Validation (Step 3):** Checked every task's files/behavior against `Architecture
Boundaries`. `GET /sla` is a net-new endpoint on a not-yet-existing contract — squarely
"Autonomous (Agent May Decide): Adding new mock endpoints that extend (not break) the existing
contract." No task touches auth, adds a workspace-repo dependency, or requires permission
boundaries on the MCP layer (Principle 5 is not implicated — this spec defines no MCP tool).
`governance/boundaries.yaml` has `boundaries: []` — no file-pattern rules to check against. No
task in this plan is marked `[REQUIRES HUMAN APPROVAL]`. `requirements.txt` is
`incident-lifecycle.plan.md` Task 1's responsibility (cross-plan foundation), not this plan's —
this plan adds no new pip dependency.

**Review notes carried forward (PASS_WITH_NOTES, `sla-records.review.md`):**
- **SA-1** (warning) — the spec's "empty array" language for BEH-2's no-match and BEH-6 doesn't
  say whether the empty-result response keeps the same paginated envelope as every other page.
  Resolved in this plan: Task 2 and Task 5 explicitly assert the response body is
  `{"items": [], "page": 1, "page_size": 50, "total": 0}` for a no-match filter — a bare `[]` is
  never returned by this implementation at any point, matched or unmatched. "Empty array" in the
  spec text refers to the `items` field's value, not the response body shape.
- **CON-1** (suggestion, advisory) — sibling list-endpoint specs are inconsistent about declaring
  an explicit pagination-parameter error case, and `sla-records.spec.md`'s own Error Cases table
  doesn't require one either. This plan does not add a task or test for invalid `page`/`page_size`
  values beyond FastAPI's automatic `int` type coercion (a non-numeric `page` value 422s
  generically via the existing literal/type-error fallback in `app/errors.py`, just with the
  generic "field is required" message rather than a tailored one). Per the review's own framing
  ("consider clarifying... during implementation" — not a blocker), this is accepted as
  out-of-scope for this plan; a dedicated pagination-validation error case is a cross-cutting
  concern better addressed once more than one list endpoint exists to generalize from.

---

## File Structure

**Create:**
- `app/routers/__init__.py` — empty package marker
- `app/routers/sla.py` — `GET /sla`
- `tests/test_sla.py` — BEH-1 through BEH-7 and both `VALIDATION_ERROR` cases

**Modify (extending files `incident-lifecycle.plan.md`'s Task 1 already created — cross-plan
dependency, not created fresh by this plan):**
- `app/models.py` — add `TaskSlaRead`, `PaginatedTaskSla` Pydantic models
- `app/main.py` — include the `sla` router
- `tests/conftest.py` — add a `seed_task_sla` helper alongside the existing `client`/`conn`
  fixtures (this spec has no `POST /sla`, so tests populate fixture rows straight into the table)

**Reference (read, do not modify — created by `incident-lifecycle.plan.md`'s Task 1, the charter's
canonical foundation; cross-plan dependency, not created by this plan):**
- `app/db.py` — `get_connection(db_path)`, `create_schema(conn)` (already creates the `task_sla`
  table, among all six charter tables)
- `app/errors.py` — `RequestValidationError`/`StarletteHTTPException` handlers, already
  generalized to translate `literal_error` and `bool_parsing`/`bool_type` error types into
  `{"message", "code": "VALIDATION_ERROR"}` JSON envelopes naming the invalid field and its
  allowed values — no change needed for this plan's `breached`/`sla_definition` filters
- `app/pagination.py` — shared pagination helper (not used directly by this plan — `GET /sla`
  does its own SQL-level `LIMIT`/`OFFSET` pagination, matching the shared `{"items", "page",
  "page_size", "total"}` envelope shape)
- `requirements.txt` — `fastapi`, `uvicorn[standard]`, `pydantic`, `pytest`, `httpx`, `ruff`
- `tests/conftest.py`'s `client`/`conn` fixtures (isolated temp-SQLite `TestClient` + connection
  per test, full six-table schema pre-applied)
- `PRD.md` — "Data model" section's `task_sla` table definition (field names/types/notes),
  "API surface" section's `GET /sla` filter list
- `.context-index/specs/features/itsm-api/charter.md` — Capability Map ("List SLA records"),
  Domain Model → TaskSla entity, Quality Attributes (pagination required on every list endpoint)
- `CLAUDE.md` — Non-Negotiable Principle 2 ("fixture-backed, offline only"), Principle 4 ("the
  HTTP contract is the boundary"), Principle 6 ("seeded discrepancies are load-bearing, not
  bugs" — governs how `business_time_only` is described in code comments and docstrings: factual,
  never "TODO: fix" or similar)
- `.context-index/governance/gates.yaml` — authoritative quality-gate commands
- `../mock-jira/.context-index/specs/features/issue-tracker-api/issue-lifecycle.plan.md` —
  pattern reference only (informal, cross-repo; `mock-jira` is sibling course infrastructure, not
  a runtime or code dependency of this repo, so reading its plan for router/error-envelope/
  `TestClient`-fixture conventions introduces no dependency and is consistent with this
  constitution's "Patterns to Follow: follow `mock-jira`'s shape")

---

## Context Packets

> No `source-manifest.files[]` exists on this spec (nothing has been implemented in this repo
> yet). No ADRs, no samples, no `orientation/architecture.md` exist for this module. Context
> packets fall back to charter + spec + constitution + PRD.md's Data Model/API-surface sections
> (standing in for orientation) + the `mock-jira` sibling-repo plan as an external pattern
> reference, per Step 2's "no source-manifest" fallback.

### Task 1 Context
- Spec: Preconditions (`business_time_only` is a stored fact, no unit conversion, no FK
  enforcement implied for reads); Charter Domain Model → TaskSla entity full field list;
  BEH-1 (unfiltered paginated page); Charter capability "List SLA records"
- PRD.md: "Data model" → `task_sla` table (field names, types, "Set true for resolution SLAs" note)
- Constitution: Principle 2 (fixture-backed/offline — SQLite only, no network), Coding Standards
  → "File structure: not yet established... follow `mock-jira`'s shape"
- **Cross-plan dependency:** `incident-lifecycle.plan.md` Task 1 — `app/db.py`'s
  `create_schema()` already defines the `task_sla` table; `app/models.py`, `app/errors.py`,
  `app/main.py`, `requirements.txt`, `tests/conftest.py` (`client`/`conn` fixtures) already exist.
  Full read of `app/db.py`, `app/models.py`, `app/errors.py`, `app/main.py`, `tests/conftest.py`
  before starting — extending these files, not recreating them.
- Pattern reference: `mock-jira/.../issue-lifecycle.plan.md` Task 1 (scaffold shape naming
  conventions) and Task 2/3 (router structure, `request.app.state.db_conn` access,
  `HTTPException(detail={"message","code"})` shape)

### Task 2 Context
- Spec: BEH-2, BEH-6 (partial — unknown `incident_number`), Error Cases table ("Unknown
  `incident_number` filter value" row: `200 OK` with empty array, not an error)
- Review note SA-1 (empty-result envelope shape — resolved here, see plan header)

### Task 3 Context
- Spec: BEH-3, Error Cases table ("Invalid `breached` value" row: `422`, `VALIDATION_ERROR`)

### Task 4 Context
- Spec: BEH-4, Error Cases table ("Invalid `sla_definition` value" row: `422`,
  `VALIDATION_ERROR`, naming allowed values)

### Task 5 Context
- Spec: BEH-5 (intersection of all given filters), BEH-6 (full — combined filters matching
  nothing), BEH-7 (`business_time_only` present/boolean/`true` for every `resolution` record)
- Charter Invariants (inherited): "`task_sla.business_time_only` is `true` for resolution SLAs —
  this is the seeded discrepancy's mechanism, not a bug"
- Constitution Principle 6 — governs how this task's docstrings/comments describe
  `business_time_only`: factually, as a measurement-method field, never as something to reconcile
  or "fix"

---

## Parallelization

- Group A (sequential): Task 1 → Task 2 → Task 3 → Task 4 → Task 5

All five tasks build the same small file set incrementally — `app/models.py` is extended once in
Task 1 and never touched again by this plan; `app/routers/sla.py` and `tests/test_sla.py` are
created in Task 1 and extended by every task after it. No independent group exists in this plan.

**Depends on (cross-plan):** Task 1 depends on `incident-lifecycle.plan.md` Task 1 (the charter's
canonical foundation — `app/db.py`'s `create_schema()` already defines the `task_sla` table;
`app/models.py`, `app/errors.py`, `app/main.py`, `requirements.txt`, `tests/conftest.py` already
exist). This plan cannot begin until that task has landed.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Implement `GET /sla` — unfiltered, paginated (BEH-1) | medium | unit | *(cross-plan)* incident-lifecycle Task 1 | 2 create, 3 modify |
| 2 | `incident_number` filter + empty-envelope shape (BEH-2, BEH-6 partial) | small | unit | Task 1 | 0 create, 2 modify |
| 3 | `breached` filter + invalid-value 422 (BEH-3) | small | unit | Task 2 | 0 create, 1 modify |
| 4 | `sla_definition` filter + invalid-value 422 (BEH-4) | small | unit | Task 3 | 0 create, 1 modify |
| 5 | Combined-filter intersection, full BEH-6, `business_time_only` correctness (BEH-5, BEH-6, BEH-7) | small | unit | Task 4 | 0 create, 1 modify |

All tasks resolve to the `unit` strategy (source: fallback — no `test_strategy` in spec
frontmatter, no `test_strategies` entries in `manifest.yaml`). Per Step 5, the Strategy Summary
section is omitted since every task is `unit`.

**Granularity:** `per-behavior` (source: manifest — `test_policy.granularity: per-behavior` in
`.context-index/manifest.yaml`). `tests/test_sla.py` is created once (Task 1, covering BEH-1) and
extended four times (Task 2 for BEH-2/BEH-6-partial, Task 3 for BEH-3, Task 4 for BEH-4, Task 5
for BEH-5/BEH-6-full/BEH-7). No separate schema task or `tests/test_db.py` exists in this plan —
`incident-lifecycle.plan.md` Task 1's `create_schema()` already defines and tests the `task_sla`
table as part of the charter-wide foundation.

---

## Task Structure

### Task 1: Implement `GET /sla` — unfiltered, paginated (BEH-1) [specialist: none]

**Charter capability:** List SLA records
**Depends on:** *(cross-plan)* `incident-lifecycle.plan.md` Task 1 — the charter's canonical
foundation. `app/db.py`'s `create_schema()` already defines the `task_sla` table; `app/models.py`,
`app/errors.py`, `app/main.py`, `requirements.txt`, and `tests/conftest.py` (`client`/`conn`
fixtures) already exist and are extended here, not recreated.
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `app/routers/__init__.py`, `app/routers/sla.py`
- Modify: `app/models.py` — add `TaskSlaRead`, `PaginatedTaskSla`
- Modify: `app/main.py` — include the `sla` router
- Modify: `tests/conftest.py` — add `seed_task_sla()` helper
- Test: `tests/test_sla.py` (create)

**Tests:** `tests/test_sla.py` (create — first task to touch this behavior; covers BEH-1)

**Context to load:**
- Spec BEH-1: "no query parameters ... `200` with a paginated page of every TaskSla record";
  Preconditions (`business_time_only` is a stored fact, no unit conversion, no FK enforcement
  implied for reads)
- Charter Quality Attributes: "pagination is required on every list endpoint"; Domain Model →
  TaskSla entity full field list
- PRD.md "Data model" → `task_sla` table
- `incident-lifecycle.plan.md` Task 1's `app/db.py`, `app/models.py`, `app/errors.py`,
  `app/main.py`, `tests/conftest.py` (full read — extending, not replacing)
- `mock-jira/.../issue-lifecycle.plan.md` Task 2 — router/error-envelope/`TestClient` pattern

- [ ] **Write failing test**

```python
# app/models.py (append — extends incident-lifecycle Task 1's file)
from typing import Literal

SLA_DEFINITIONS = ("first_response", "resolution")


class TaskSlaRead(BaseModel):
    sys_id: str
    incident_number: str
    sla_definition: Literal["first_response", "resolution"]
    target_minutes: int
    actual_minutes: int | None
    has_breached: bool
    business_time_only: bool


class PaginatedTaskSla(BaseModel):
    items: list[TaskSlaRead]
    page: int
    page_size: int
    total: int
```

`has_breached` and `business_time_only` are stored in `task_sla` as SQLite `INTEGER` (0/1) —
SQLite has no native boolean type; `TaskSlaRead` converts them to Python `bool` on read (below).
`incident_number` deliberately carries no `REFERENCES incidents(number)` clause in
`incident-lifecycle.plan.md`'s `create_schema()` statement for `task_sla` — see this plan's
Architecture note on why this table has no enforced FK.

```python
# tests/conftest.py (append — extends incident-lifecycle Task 1's file)
def seed_task_sla(conn, **overrides):
    row = {
        "sys_id": "SLA-0001",
        "incident_number": "TICKET-000001",
        "sla_definition": "first_response",
        "target_minutes": 30,
        "actual_minutes": 20,
        "has_breached": 0,
        "business_time_only": 0,
    }
    row.update(overrides)
    conn.execute(
        """
        INSERT INTO task_sla
            (sys_id, incident_number, sla_definition, target_minutes, actual_minutes,
             has_breached, business_time_only)
        VALUES (:sys_id, :incident_number, :sla_definition, :target_minutes, :actual_minutes,
                :has_breached, :business_time_only)
        """,
        row,
    )
    conn.commit()
    return row
```

```python
# tests/test_sla.py
from tests.conftest import seed_task_sla


def test_get_sla_unfiltered_returns_paginated_page_of_all_records(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", incident_number="TICKET-000001")
    seed_task_sla(conn, sys_id="SLA-0002", incident_number="TICKET-000002")

    resp = client.get("/sla")

    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert {item["sys_id"] for item in body["items"]} == {"SLA-0001", "SLA-0002"}
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_sla.py`
Expected: FAIL — `404 Not Found` (no `/sla` route registered yet; `app/routers/sla.py` doesn't
exist).

- [ ] **Implement**

```python
# app/routers/__init__.py
# (empty — package marker)
```

```python
# app/routers/sla.py
from fastapi import APIRouter, Request

from app.models import PaginatedTaskSla, TaskSlaRead

router = APIRouter()


def _row_to_task_sla_read(row) -> TaskSlaRead:
    return TaskSlaRead(
        sys_id=row["sys_id"],
        incident_number=row["incident_number"],
        sla_definition=row["sla_definition"],
        target_minutes=row["target_minutes"],
        actual_minutes=row["actual_minutes"],
        has_breached=bool(row["has_breached"]),
        business_time_only=bool(row["business_time_only"]),
    )


@router.get("/sla", response_model=PaginatedTaskSla)
def list_sla_records(request: Request, page: int = 1, page_size: int = 50):
    conn = request.app.state.db_conn
    total = conn.execute("SELECT COUNT(*) AS c FROM task_sla").fetchone()["c"]
    rows = conn.execute(
        "SELECT * FROM task_sla ORDER BY sys_id ASC LIMIT ? OFFSET ?",
        (page_size, (page - 1) * page_size),
    ).fetchall()
    items = [_row_to_task_sla_read(r) for r in rows]
    return PaginatedTaskSla(items=items, page=page, page_size=page_size, total=total)
```

```python
# app/main.py (modify)
from app.routers.sla import router as sla_router

# inside create_app, before `return app`:
app.include_router(sla_router)
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_sla.py`
Expected: PASS

- [ ] **Commit**

Branch: `feat/itsm-api/sla-records-list`

```bash
git checkout -b feat/itsm-api/sla-records-list
git add app/models.py app/main.py app/routers/__init__.py app/routers/sla.py \
        tests/conftest.py tests/test_sla.py
git commit -m "feat(itsm-api): implement GET /sla with unfiltered pagination"
```

---

### Task 2: `incident_number` filter + empty-envelope shape (BEH-2, BEH-6 partial) [specialist: none]

**Charter capability:** List SLA records
**Depends on:** Task 1
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/sla.py` — add `incident_number` filter
- Modify: `tests/test_sla.py` — extend
- Test: `tests/test_sla.py`

**Tests:** `tests/test_sla.py` (extend — BEH-2, BEH-6's `incident_number` no-match case; suite
already created by Task 1)

**Context to load:**
- Spec BEH-2, BEH-6, Error Cases table ("Unknown `incident_number` filter value" → `200` with
  empty array)
- Review note SA-1 — resolved by asserting the full envelope shape, not a bare `[]`

- [ ] **Write failing test**

```python
# tests/test_sla.py (append)
def test_get_sla_filtered_by_incident_number_returns_matching_records_only(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", incident_number="TICKET-000001",
                  sla_definition="first_response")
    seed_task_sla(conn, sys_id="SLA-0002", incident_number="TICKET-000001",
                  sla_definition="resolution")
    seed_task_sla(conn, sys_id="SLA-0003", incident_number="TICKET-000002")

    resp = client.get("/sla?incident_number=TICKET-000001")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert {item["sys_id"] for item in body["items"]} == {"SLA-0001", "SLA-0002"}


def test_get_sla_unknown_incident_number_returns_200_with_empty_paginated_envelope(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", incident_number="TICKET-000001")

    resp = client.get("/sla?incident_number=TICKET-999999")

    assert resp.status_code == 200
    body = resp.json()
    # SA-1: the full paginated envelope, never a bare [] — "empty array" in the spec refers only
    # to the items field's value.
    assert body == {"items": [], "page": 1, "page_size": 50, "total": 0}
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_sla.py::test_get_sla_filtered_by_incident_number_returns_matching_records_only tests/test_sla.py::test_get_sla_unknown_incident_number_returns_200_with_empty_paginated_envelope`
Expected: FAIL — both requests return the full unfiltered set (Task 1's implementation ignores
`incident_number`), so the first test's `total == 2` assertion fails (actual: 3) and the second's
empty-envelope assertion fails (actual: 1 item).

- [ ] **Implement**

```python
# app/routers/sla.py (modify list_sla_records)
@router.get("/sla", response_model=PaginatedTaskSla)
def list_sla_records(
    request: Request,
    incident_number: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    conn = request.app.state.db_conn
    query = "SELECT * FROM task_sla WHERE 1=1"
    params: list = []
    if incident_number is not None:
        query += " AND incident_number = ?"
        params.append(incident_number)

    total = conn.execute(
        f"SELECT COUNT(*) AS c FROM ({query})", params
    ).fetchone()["c"]

    query += " ORDER BY sys_id ASC LIMIT ? OFFSET ?"
    rows = conn.execute(query, [*params, page_size, (page - 1) * page_size]).fetchall()
    items = [_row_to_task_sla_read(r) for r in rows]
    return PaginatedTaskSla(items=items, page=page, page_size=page_size, total=total)
```

No `incident_number` existence check is added, by design — see plan header's Architecture note
and BEH-6: an unknown filter value is a normal zero-match query on a list endpoint, not an error.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_sla.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/sla.py tests/test_sla.py
git commit -m "feat(itsm-api): add incident_number filter to GET /sla"
```

---

### Task 3: `breached` filter + invalid-value 422 (BEH-3) [specialist: none]

**Charter capability:** List SLA records
**Depends on:** Task 2
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/sla.py` — add `breached` filter
- Modify: `tests/test_sla.py` — extend
- Test: `tests/test_sla.py`

**Tests:** `tests/test_sla.py` (extend — BEH-3, plus the invalid-`breached`-value `422` Error
Case; suite already created by Task 1)

**Context to load:**
- Spec BEH-3, Error Cases table ("Invalid `breached` value" → `422`, `VALIDATION_ERROR`)

- [ ] **Write failing test**

```python
# tests/test_sla.py (append)
def test_get_sla_filtered_by_breached_true(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", has_breached=1)
    seed_task_sla(conn, sys_id="SLA-0002", has_breached=0)

    resp = client.get("/sla?breached=true")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["sys_id"] == "SLA-0001"
    assert body["items"][0]["has_breached"] is True


def test_get_sla_filtered_by_breached_false(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", has_breached=1)
    seed_task_sla(conn, sys_id="SLA-0002", has_breached=0)

    resp = client.get("/sla?breached=false")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["sys_id"] == "SLA-0002"


def test_get_sla_invalid_breached_value_returns_422(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001")

    resp = client.get("/sla?breached=maybe")

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "breached" in body["message"]
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_sla.py::test_get_sla_filtered_by_breached_true tests/test_sla.py::test_get_sla_filtered_by_breached_false tests/test_sla.py::test_get_sla_invalid_breached_value_returns_422`
Expected: FAIL on the two filter tests — `breached` is ignored so `total` is 2 in both, not 1;
`test_get_sla_invalid_breached_value_returns_422` unexpectedly PASSES already, because FastAPI has
no `breached` query parameter declared yet so `?breached=maybe` is silently ignored rather than
422ing — confirming this specific test only becomes meaningful once `breached: bool | None` is
declared, at which point it must be re-verified to still pass for the right reason (see next step).

- [ ] **Implement**

```python
# app/routers/sla.py (modify list_sla_records)
@router.get("/sla", response_model=PaginatedTaskSla)
def list_sla_records(
    request: Request,
    incident_number: str | None = None,
    breached: bool | None = None,
    page: int = 1,
    page_size: int = 50,
):
    conn = request.app.state.db_conn
    query = "SELECT * FROM task_sla WHERE 1=1"
    params: list = []
    if incident_number is not None:
        query += " AND incident_number = ?"
        params.append(incident_number)
    if breached is not None:
        query += " AND has_breached = ?"
        params.append(1 if breached else 0)

    total = conn.execute(
        f"SELECT COUNT(*) AS c FROM ({query})", params
    ).fetchone()["c"]

    query += " ORDER BY sys_id ASC LIMIT ? OFFSET ?"
    rows = conn.execute(query, [*params, page_size, (page - 1) * page_size]).fetchall()
    items = [_row_to_task_sla_read(r) for r in rows]
    return PaginatedTaskSla(items=items, page=page, page_size=page_size, total=total)
```

Declaring `breached: bool | None = None` is what makes `?breached=maybe` raise
`RequestValidationError` with error type `bool_parsing` — already handled generically by
`incident-lifecycle.plan.md`'s (cross-plan) Task 1 `validation_exception_handler`, so no change to
`app/errors.py` or `app/main.py` is needed for this task.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_sla.py`
Expected: PASS — including re-confirming `test_get_sla_invalid_breached_value_returns_422` now
passes because of the declared `bool` type, not by coincidence.

- [ ] **Commit**

```bash
git add app/routers/sla.py tests/test_sla.py
git commit -m "feat(itsm-api): add breached filter to GET /sla with 422 on invalid value"
```

---

### Task 4: `sla_definition` filter + invalid-value 422 (BEH-4) [specialist: none]

**Charter capability:** List SLA records
**Depends on:** Task 3
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/sla.py` — add `sla_definition` filter
- Modify: `app/models.py` — no functional change; `SLA_DEFINITIONS` constant from Task 1 is now
  actually referenced (used for a comment cross-reference, not re-declared)
- Modify: `tests/test_sla.py` — extend
- Test: `tests/test_sla.py`

**Tests:** `tests/test_sla.py` (extend — BEH-4, plus the invalid-`sla_definition`-value `422`
Error Case; suite already created by Task 1)

**Context to load:**
- Spec BEH-4, Error Cases table ("Invalid `sla_definition` value" → `422`, `VALIDATION_ERROR`,
  naming allowed values)

- [ ] **Write failing test**

```python
# tests/test_sla.py (append)
def test_get_sla_filtered_by_sla_definition_first_response(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", sla_definition="first_response")
    seed_task_sla(conn, sys_id="SLA-0002", sla_definition="resolution")

    resp = client.get("/sla?sla_definition=first_response")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["sys_id"] == "SLA-0001"


def test_get_sla_filtered_by_sla_definition_resolution(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", sla_definition="first_response")
    seed_task_sla(conn, sys_id="SLA-0002", sla_definition="resolution")

    resp = client.get("/sla?sla_definition=resolution")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["sys_id"] == "SLA-0002"


def test_get_sla_invalid_sla_definition_value_returns_422_naming_allowed_values(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001")

    resp = client.get("/sla?sla_definition=escalation_response")

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "sla_definition" in body["message"]
    assert "first_response" in body["message"] and "resolution" in body["message"]
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_sla.py::test_get_sla_filtered_by_sla_definition_first_response tests/test_sla.py::test_get_sla_filtered_by_sla_definition_resolution tests/test_sla.py::test_get_sla_invalid_sla_definition_value_returns_422_naming_allowed_values`
Expected: FAIL — `sla_definition` is not yet a declared query parameter, so it's silently ignored:
both filter tests see `total == 2`, and the invalid-value test gets `200` instead of `422`.

- [ ] **Implement**

```python
# app/routers/sla.py (modify list_sla_records)
from typing import Literal


@router.get("/sla", response_model=PaginatedTaskSla)
def list_sla_records(
    request: Request,
    incident_number: str | None = None,
    breached: bool | None = None,
    sla_definition: Literal["first_response", "resolution"] | None = None,
    page: int = 1,
    page_size: int = 50,
):
    conn = request.app.state.db_conn
    query = "SELECT * FROM task_sla WHERE 1=1"
    params: list = []
    if incident_number is not None:
        query += " AND incident_number = ?"
        params.append(incident_number)
    if breached is not None:
        query += " AND has_breached = ?"
        params.append(1 if breached else 0)
    if sla_definition is not None:
        query += " AND sla_definition = ?"
        params.append(sla_definition)

    total = conn.execute(
        f"SELECT COUNT(*) AS c FROM ({query})", params
    ).fetchone()["c"]

    query += " ORDER BY sys_id ASC LIMIT ? OFFSET ?"
    rows = conn.execute(query, [*params, page_size, (page - 1) * page_size]).fetchall()
    items = [_row_to_task_sla_read(r) for r in rows]
    return PaginatedTaskSla(items=items, page=page, page_size=page_size, total=total)
```

The `Literal["first_response", "resolution"]` type is what makes an out-of-set value raise
`literal_error` — already handled generically by `incident-lifecycle.plan.md`'s (cross-plan)
Task 1 `validation_exception_handler`, which reports `ctx.expected` (Pydantic's human-readable
allowed-values string), satisfying "naming the invalid field and its allowed values" with no
`sla_definition`-specific code in `app/errors.py`. No change to `app/errors.py` is needed for this
task.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_sla.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/sla.py tests/test_sla.py
git commit -m "feat(itsm-api): add sla_definition filter to GET /sla with 422 on invalid value"
```

---

### Task 5: Combined-filter intersection, full BEH-6, `business_time_only` correctness (BEH-5, BEH-6, BEH-7) [specialist: none]

**Charter capability:** List SLA records
**Depends on:** Task 4
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `tests/test_sla.py` — extend (no `app/routers/sla.py` change expected — see below)
- Test: `tests/test_sla.py`

**Tests:** `tests/test_sla.py` (extend — BEH-5, BEH-6 full combined-filter case, BEH-7; suite
already created by Task 1)

**Context to load:**
- Spec BEH-5 (intersection of all given filters), BEH-6 (combined filters matching nothing),
  BEH-7 (`business_time_only` present/boolean/`true` for every `resolution` record)
- Charter Invariants: "`task_sla.business_time_only` is `true` for resolution SLAs — this is the
  seeded discrepancy's mechanism, not a bug"
- Constitution Principle 6 — describe `business_time_only` factually in any new comment/docstring

- [ ] **Write failing test**

```python
# tests/test_sla.py (append)
def test_get_sla_combined_filters_narrow_to_intersection(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", incident_number="TICKET-000001",
                  sla_definition="resolution", has_breached=1)
    seed_task_sla(conn, sys_id="SLA-0002", incident_number="TICKET-000001",
                  sla_definition="first_response", has_breached=1)
    seed_task_sla(conn, sys_id="SLA-0003", incident_number="TICKET-000002",
                  sla_definition="resolution", has_breached=1)

    resp = client.get(
        "/sla?incident_number=TICKET-000001&breached=true&sla_definition=resolution"
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["sys_id"] == "SLA-0001"


def test_get_sla_combined_filters_matching_nothing_returns_empty_paginated_envelope(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", incident_number="TICKET-000001",
                  sla_definition="first_response", has_breached=0)

    resp = client.get(
        "/sla?incident_number=TICKET-000001&breached=true&sla_definition=resolution"
    )

    assert resp.status_code == 200
    assert resp.json() == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_get_sla_business_time_only_present_and_true_for_every_resolution_record(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", sla_definition="resolution",
                  business_time_only=1)
    seed_task_sla(conn, sys_id="SLA-0002", sla_definition="first_response",
                  business_time_only=0)

    resp = client.get("/sla")

    assert resp.status_code == 200
    items = {item["sys_id"]: item for item in resp.json()["items"]}
    assert isinstance(items["SLA-0001"]["business_time_only"], bool)
    assert items["SLA-0001"]["business_time_only"] is True
    assert isinstance(items["SLA-0002"]["business_time_only"], bool)
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_sla.py::test_get_sla_combined_filters_narrow_to_intersection tests/test_sla.py::test_get_sla_combined_filters_matching_nothing_returns_empty_paginated_envelope tests/test_sla.py::test_get_sla_business_time_only_present_and_true_for_every_resolution_record`

Expected: all three PASS immediately without any code change — Tasks 2-4 already compose their
filters with `AND` into a single query, and Task 1's `_row_to_task_sla_read` already converts
`business_time_only` to `bool` on every row. This step exists to prove BEH-5/BEH-6-full/BEH-7 are
genuine, tested consequences of the prior four tasks' implementation rather than assumed —
per this plan's TDD discipline, the assertion is written and run before being declared covered,
even though no red-to-green code change follows.

- [ ] **Implement**

No implementation change. If the "Verify test fails" step above surfaces an unexpected failure
(e.g., a filter composition bug not caught by Tasks 3-5's narrower tests), fix it in
`app/routers/sla.py` here and re-run; this task's own code-change budget covers exactly and only
that contingency.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q`
Expected: PASS — full suite, confirming BEH-1 through BEH-7 and both `422` Error Cases all hold
together.

- [ ] **Commit**

```bash
git add tests/test_sla.py
git commit -m "test(itsm-api): verify combined-filter intersection, empty-match envelope, and business_time_only correctness for GET /sla"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are
recorded in the validation report (`.validate.md`), not in this plan.

`.context-index/governance/gates.yaml` exists and is used in place of the constitution's generic
gate list:

- **Test Suite** (`test`, deterministic, required, severity error): `python3 -m pytest -q`
- **Linter** (`lint`, deterministic, required, severity error): `ruff check .`
- **Integration Tests** (`integration-test`, deterministic, required): command is unwired
  (`command: ""` in `gates.yaml`). This gate is **skipped** for this plan; nothing in this plan's
  task list requires an integration suite beyond the unit-level `TestClient` coverage above.
- All acceptance criteria from `sla-records.spec.md` satisfied (BEH-1 through BEH-7, both
  `VALIDATION_ERROR` cases, empty-envelope shape per SA-1).
