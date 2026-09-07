# Implementation Plan: Escalation list, get, and update

> **Methodology:** adev
> **Charter:** .context-index/specs/features/itsm-api/charter.md
> **Spec:** .context-index/specs/features/itsm-api/escalations.spec.md
> **Review:** PASS_WITH_NOTES (2026-09-07)
> **Platform:** FastAPI (per constitution's "follow mock-jira's shape" guidance), Python 3.11, SQLite, Pydantic

**Goal:** Implement the read/update HTTP surface for Escalations (`GET /escalations`,
`GET /escalations/{number}`, `PATCH /escalations/{number}`) with account_id/open_only filtering,
pagination, and null-safe handling of the two seeded ownerless escalations.

**Architecture:** This repo is greenfield. Per a cross-plan consistency pass (2026-09-07),
`incident-lifecycle.plan.md`'s Task 1 is this charter's designated canonical foundation owner: it
creates `app/db.py` (with `create_schema()` already covering **all six** charter tables,
including `escalations`), `app/models.py`, `app/errors.py`, `app/main.py`, `app/pagination.py`,
`requirements.txt`, and `tests/conftest.py` (the `client`/`conn` fixtures). This plan's Task 1
**depends on** that foundation and **extends** `app/models.py` with this spec's own
`EscalationRead`/`EscalationPatch`/`EscalationPage` models — it does not recreate the `escalations`
table in `create_schema()` (already defined there) or any of the other shared files. Because no
other spec in this charter had landed a table before `incident-lifecycle`'s foundation, this
plan's own `Escalation.incident_number` remains a plain nullable `TEXT` column with **no enforced
SQL foreign-key constraint** to `incidents` (matching `incident-lifecycle`'s own `create_schema()`
statement for `escalations`, which likewise omits the FK) — this mirrors how the charter's own
Domain Model already treats `Incident.assigned_to`/`assignment_group` as free-text references
rather than enforced FKs. `EscalationPatch` (Task 1) deliberately has no `number`, `account_id`,
`opened_at`, or `incident_number` field at all, so PATCH's immutable-field handling (BEH-6) is
enforced structurally by Pydantic dropping unrecognized keys, not by a runtime allow/deny check
that could regress.

**Constitution Validation (Step 3):** Checked every task's files/behavior against `Architecture
Boundaries`. No task adds a workspace-repo dependency, touches auth, or breaks an already-shipped
contract (nothing is shipped yet). `governance/boundaries.yaml` has `boundaries: []`, so no
file-pattern flags apply. No task is marked `[REQUIRES HUMAN APPROVAL]`. `requirements.txt` and
the baseline web-framework pip dependencies (`fastapi`, `uvicorn[standard]`, `pydantic`, `pytest`,
`httpx`, `ruff`) are `incident-lifecycle.plan.md` Task 1's responsibility (cross-plan foundation),
not this plan's — this plan adds no new pip dependency.

**Review notes carried forward (PASS_WITH_NOTES, 3 findings, 0 blockers):**
- **SA-1** (warning) — BEH-6 names `number`/`account_id`/`opened_at` as immutable/silently-ignored
  but does not mention `incident_number`, a nullable FK per the charter's Domain Model, leaving its
  PATCH behavior technically unstated. Resolved in code, not by editing the reviewed spec text:
  Task 1's `EscalationPatch` model has no `incident_number` field, so Task 3's `UPDATE` statement
  has no path to write it regardless of request body content — identical structural treatment to
  the three fields BEH-6 does name. Task 3's tests assert this explicitly.
- **SA-2** (suggestion) — BEH-7 explicitly states `owner: null` is a valid unassignment; no
  equivalent statement exists for reopening via `closed_at: null`. Resolved in code: Task 3's PATCH
  handler treats `closed_at` exactly like `owner` — `exclude_unset=True` lets an explicit JSON
  `null` reach the `UPDATE`, distinct from an omitted field — and a test proves a
  reopened Escalation reappears in `GET /escalations?open_only=true`.
- **CON-1** (suggestion) — the Error Cases table doesn't explicitly state that an unmatched
  `account_id`/`open_only` filter returns `200` with an empty page (the sibling `sla-records.spec.md`
  does state this for its own filters). Resolved in code: Task 1's list query has no
  "filter matched nothing" special case — an unmatched filter falls through the same `WHERE`-clause
  path as any other and returns `200` with `items: []`, `total: 0` by construction. A test
  (`test_list_escalations_unknown_account_id_returns_200_empty_page`) pins this down.

---

## File Structure

**Create:**
- `app/routers/__init__.py` — empty package marker
- `app/routers/escalations.py` — `GET /escalations`, `GET /escalations/{number}`,
  `PATCH /escalations/{number}`
- `tests/test_escalations.py` — BEH-1 through BEH-8 coverage

**Modify (extending files `incident-lifecycle.plan.md`'s Task 1 already created — cross-plan
dependency, not created fresh by this plan):**
- `app/models.py` — add `EscalationRead`, `EscalationPatch`, `EscalationPage` Pydantic models
- `app/main.py` — include the `escalations` router
- `tests/conftest.py` — add a `seed_escalation()` helper alongside the existing `client`/`conn`
  fixtures

**Reference (read, do not modify — created by `incident-lifecycle.plan.md`'s Task 1, the charter's
canonical foundation; cross-plan dependency, not created by this plan):**
- `app/db.py` — `get_connection(db_path)`, `create_schema(conn)` (already creates the
  `escalations` table, among all six charter tables)
- `app/errors.py` — `http_exception_handler`, `validation_exception_handler` — structured JSON
  error envelope (`{"message": ..., "code": ...}`), generalized to cover this plan's own
  `open_only` boolean-validation error case with no changes needed
- `app/pagination.py` — shared pagination helper (not used directly by this plan — `GET
  /escalations` does its own SQL-level `LIMIT`/`OFFSET` pagination, matching the shared
  `{"items", "page", "page_size", "total"}` envelope shape)
- `requirements.txt` — `fastapi`, `uvicorn[standard]`, `pydantic`, `pytest`, `httpx`, `ruff`
- `tests/conftest.py`'s `client`/`conn` fixtures (isolated temp-SQLite `TestClient` + connection
  per test, full six-table schema pre-applied)
- `.context-index/specs/features/itsm-api/charter.md` — Domain Model (Escalation entity),
  Capability Map, Architecture Boundaries
- `CLAUDE.md` — constitution: Principle 6 (the two ownerless escalations are load-bearing, never
  "fixed"), Principle 4 (HTTP contract is the boundary), Coding Standards ("follow mock-jira's
  shape")
- `PRD.md` — `escalation` table schema (lines 84-96), API surface block (lines 137-146:
  `GET/PATCH /escalations`, "pagination on every list endpoint")
- `.context-index/governance/gates.yaml` — authoritative quality-gate commands (`test`, `lint`,
  unwired `integration-test`)

---

## Context Packets

> No `source-manifest.files[]` exists on this spec (nothing has been implemented yet in this
> repo). This module has no ADRs, no samples, and no `orientation/architecture.md`. Context
> packets fall back to charter + spec + constitution + PRD.md, per Step 2's "no source-manifest"
> fallback. `adev heuristics retrieve --module itsm-api` returned `__NONE__`.

### Task 1 Context
- Spec: BEH-1, BEH-2, BEH-3; Error Cases table (`VALIDATION_ERROR` for invalid `open_only`);
  review note **CON-1** (unmatched filter → `200` empty page, resolved here); Preconditions
  ("`incident_number` and `owner` are both nullable... not something any endpoint... treats as
  exceptional")
- Charter: Capability "List/get/update Escalations"; Domain Model → Escalation entity (`number`
  PK, `incident_number` FK nullable, `account_id`, `summary`, `opened_at`, `closed_at`, `owner`
  nullable); Quality Attributes → "pagination is required on every list endpoint"
- PRD.md: `escalation` table (lines 84-96); `GET /escalations filter: account_id, open_only`
  (line 137)
- **Cross-plan dependency:** `incident-lifecycle.plan.md` Task 1 — `app/db.py`'s
  `create_schema()` already defines the `escalations` table; `app/models.py`, `app/errors.py`,
  `app/main.py`, `requirements.txt`, `tests/conftest.py` (`client`/`conn` fixtures) already exist.
  Full read of `app/db.py`, `app/models.py`, `app/errors.py`, `app/main.py`, `tests/conftest.py`
  before starting — extending these files, not recreating them.
- Boundary rules: `.context-index/governance/boundaries.yaml` — empty, no rules to apply
- Heuristics: none available for module `itsm-api`

### Task 2 Context
- Spec: BEH-4, BEH-5; Error Cases table (`ESCALATION_NOT_FOUND`)
- Charter: Capability "List/get/update Escalations"
- Source files: `app/routers/escalations.py` (from Task 1, full read — extending)

### Task 3 Context
- Spec: BEH-6, BEH-7, BEH-8; Postconditions ("An Escalation's `number` and `account_id` never
  change once seeded"; "Setting `closed_at` to a non-null value removes that Escalation from
  subsequent `open_only=true` results"); Error Cases table (`ESCALATION_NOT_FOUND`,
  `MALFORMED_JSON`)
- Charter: Capability "List/get/update Escalations"; Constitution Principle 6 (ownerless
  escalations are load-bearing — `owner: null` PATCH must succeed, never be rejected or defaulted)
- Review notes: **SA-1** (`incident_number` immutability — enforced structurally, see plan
  header), **SA-2** (`closed_at: null` reopen — same `exclude_unset` mechanism as `owner: null`)
- Source files: `app/routers/escalations.py` (from Task 1-2, full read — extending)

---

## Parallelization

- Group A (sequential): Task 1 → Task 2 → Task 3

All three tasks are sequential: Task 1 extends the shared `app/models.py` with this plan's
Escalation models and creates `app/routers/escalations.py`, which Tasks 2-3 both extend further,
along with `tests/test_escalations.py`, so no independent group exists within this plan.

**Depends on (cross-plan):** Task 1 depends on `incident-lifecycle.plan.md` Task 1 (the charter's
canonical foundation — `app/db.py`'s `create_schema()` already defines the `escalations` table;
`app/models.py`, `app/errors.py`, `app/main.py`, `requirements.txt`, `tests/conftest.py` already
exist). This plan cannot begin until that task has landed.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Implement `GET /escalations` with filters and pagination | medium | unit | *(cross-plan)* incident-lifecycle Task 1 | 2 create, 3 modify |
| 2 | Implement `GET /escalations/{number}` | small | unit | Task 1 | 0 create, 2 modify |
| 3 | Implement `PATCH /escalations/{number}` | medium | unit | Task 2 | 0 create, 2 modify |

All tasks resolve to the `unit` strategy (source: fallback — no `test_strategy` in spec
frontmatter, no `test_strategies` entries in `manifest.yaml` matching these paths). Per Step 5,
the Strategy Summary section is omitted since every task is `unit`.

**Granularity:** `per-behavior` (source: manifest — `test_policy.granularity: per-behavior` in
`.context-index/manifest.yaml`). `tests/test_escalations.py` is created once (Task 1, covering
BEH-1/2/3 plus CON-1's empty-page clarification) and extended twice more (Task 2 for BEH-4/5,
Task 3 for BEH-6/7/8 plus SA-1/SA-2 plus the `MALFORMED_JSON` error case). No separate schema
task or `tests/test_db.py` exists in this plan — `incident-lifecycle.plan.md` Task 1's
`create_schema()` already defines and tests the `escalations` table as part of the charter-wide
foundation.

---

## Task Structure

### Task 1: Implement `GET /escalations` with filters and pagination [specialist: none]

**Charter capability:** List/get/update Escalations
**Depends on:** *(cross-plan)* `incident-lifecycle.plan.md` Task 1 — the charter's canonical
foundation. `app/db.py`'s `create_schema()` already defines the `escalations` table; `app/models.py`,
`app/errors.py`, `app/main.py`, `requirements.txt`, and `tests/conftest.py` (`client`/`conn`
fixtures) already exist and are extended here, not recreated.
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `app/routers/__init__.py`, `app/routers/escalations.py`
- Modify: `app/models.py` — add `EscalationRead`, `EscalationPatch`, `EscalationPage`
- Modify: `app/main.py` — include the `escalations` router
- Modify: `tests/conftest.py` — add `seed_escalation()` helper
- Test: `tests/test_escalations.py` (create)

**Tests:** `tests/test_escalations.py` (create — first task to touch this behavior; covers BEH-1,
BEH-2, BEH-3, and CON-1's unmatched-filter clarification)

**Context to load:**
- Spec BEH-1, BEH-2, BEH-3; Error Cases table (`VALIDATION_ERROR` for invalid `open_only`);
  review note CON-1; Preconditions ("`incident_number` and `owner` are both nullable")
- Charter Domain Model: Escalation entity full field list
- PRD.md: `escalation` table (lines 84-96); `GET /escalations filter: account_id, open_only`
  (line 137); "pagination on every list endpoint" (line 145)
- `incident-lifecycle.plan.md` Task 1's `app/db.py`, `app/models.py`, `app/errors.py`,
  `app/main.py`, `tests/conftest.py` (full read — extending, not replacing)

- [ ] **Write failing test**

```python
# app/models.py (append — extends incident-lifecycle Task 1's file)
class EscalationRead(BaseModel):
    number: str
    incident_number: str | None
    account_id: str
    summary: str
    opened_at: str
    closed_at: str | None
    owner: str | None


class EscalationPatch(BaseModel):
    summary: str | None = None
    owner: str | None = None
    closed_at: str | None = None


class EscalationPage(BaseModel):
    items: list[EscalationRead]
    page: int
    page_size: int
    total: int
```

`EscalationPatch` has no `number`, `account_id`, `opened_at`, or `incident_number` field at all —
this is the structural enforcement of BEH-6's immutable-fields list, extended to cover SA-1's
`incident_number` ambiguity identically: none of these four keys can ever appear in
`payload.model_dump(...)` (Task 3) regardless of what the raw request JSON contains, because
Pydantic drops unrecognized fields on a `BaseModel` by default.

```python
# tests/conftest.py (append — extends incident-lifecycle Task 1's file)
def seed_escalation(conn, **overrides):
    defaults = {
        "number": "ESCALATION-0001",
        "incident_number": None,
        "account_id": "ACC-1",
        "summary": "Test escalation",
        "opened_at": "2026-01-01T00:00:00Z",
        "closed_at": None,
        "owner": None,
    }
    defaults.update(overrides)
    conn.execute(
        "INSERT INTO escalations "
        "(number, incident_number, account_id, summary, opened_at, closed_at, owner) "
        "VALUES (:number, :incident_number, :account_id, :summary, :opened_at, :closed_at, :owner)",
        defaults,
    )
    conn.commit()
    return defaults
```

```python
# app/routers/escalations.py (new file)
from fastapi import APIRouter

router = APIRouter()
```

```python
# tests/test_escalations.py
from tests.conftest import seed_escalation


def test_list_escalations_returns_paginated_page_including_null_fields(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", incident_number=None, owner=None)
    seed_escalation(conn, number="ESCALATION-0002", incident_number="TICKET-000123", owner="dana")

    resp = client.get("/escalations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["total"] == 2
    by_number = {item["number"]: item for item in body["items"]}
    assert set(by_number) == {"ESCALATION-0001", "ESCALATION-0002"}
    assert by_number["ESCALATION-0001"]["incident_number"] is None
    assert by_number["ESCALATION-0001"]["owner"] is None


def test_list_escalations_filtered_by_account_id(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", account_id="ACC-1")
    seed_escalation(conn, number="ESCALATION-0002", account_id="ACC-2")

    resp = client.get("/escalations?account_id=ACC-2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["number"] == "ESCALATION-0002"


def test_list_escalations_open_only_excludes_closed(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", closed_at=None)
    seed_escalation(conn, number="ESCALATION-0002", closed_at="2026-02-01T00:00:00Z")

    resp = client.get("/escalations?open_only=true")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["number"] == "ESCALATION-0001"


def test_list_escalations_unknown_account_id_returns_200_empty_page(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", account_id="ACC-1")

    resp = client.get("/escalations?account_id=ACC-DOES-NOT-EXIST")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_escalations_invalid_open_only_returns_422(client):
    resp = client.get("/escalations?open_only=maybe")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "open_only" in body["message"]
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_escalations.py`
Expected: FAIL — `404 Not Found` (no `GET /escalations` route registered yet).

- [ ] **Implement**

```python
# app/routers/escalations.py (append)
from fastapi import HTTPException, Request

from app.models import EscalationPage, EscalationRead


def _row_to_escalation_read(row) -> EscalationRead:
    return EscalationRead(
        number=row["number"],
        incident_number=row["incident_number"],
        account_id=row["account_id"],
        summary=row["summary"],
        opened_at=row["opened_at"],
        closed_at=row["closed_at"],
        owner=row["owner"],
    )


@router.get("/escalations", response_model=EscalationPage)
def list_escalations(
    request: Request,
    account_id: str | None = None,
    open_only: bool | None = None,
    page: int = 1,
    page_size: int = 50,
):
    conn = request.app.state.db_conn
    where: list[str] = []
    params: list = []
    if account_id is not None:
        where.append("account_id = ?")
        params.append(account_id)
    if open_only:
        where.append("closed_at IS NULL")
    clause = f"WHERE {' AND '.join(where)}" if where else ""

    total = conn.execute(
        f"SELECT COUNT(*) AS c FROM escalations {clause}", params
    ).fetchone()["c"]
    offset = (page - 1) * page_size
    rows = conn.execute(
        f"SELECT * FROM escalations {clause} ORDER BY number ASC LIMIT ? OFFSET ?",
        (*params, page_size, offset),
    ).fetchall()
    return EscalationPage(
        items=[_row_to_escalation_read(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
```

`open_only: bool | None` is FastAPI/Pydantic's native query-param boolean parsing (accepts
`true`/`false`/`1`/`0`/`yes`/`no`, case-insensitive); an unparseable value like `maybe` raises
`RequestValidationError` before this handler body ever runs, so `incident-lifecycle.plan.md`'s
(cross-plan) Task 1 `validation_exception_handler` — already generalized to cover the
`bool_parsing`/`bool_type` error types — already returns `422 VALIDATION_ERROR` naming
`open_only`, no new error-handling code needed here. A filter that matches zero rows (`account_id`
typo, or
`open_only=true` when every seeded row is closed) falls through the identical `WHERE`-clause path
as any other filter combination and returns `200` with `items: []`, `total: 0` — there is no
separate "filter matched nothing" branch, which is what makes CON-1 true by construction rather
than a special case that could be forgotten.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_escalations.py`
Expected: PASS

- [ ] **Commit**

Branch: `feat/itsm-api/escalations`

```bash
git checkout -b feat/itsm-api/escalations
git add app/models.py app/main.py app/routers/__init__.py app/routers/escalations.py \
  tests/conftest.py tests/test_escalations.py
git commit -m "feat(itsm-api): implement GET /escalations with account_id/open_only filters and pagination"
```

---

### Task 2: Implement `GET /escalations/{number}` [specialist: none]

**Charter capability:** List/get/update Escalations
**Depends on:** Task 1
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/escalations.py` — add get-by-number endpoint
- Modify: `tests/test_escalations.py` — extend

**Tests:** `tests/test_escalations.py` (extend — BEH-4, BEH-5; suite already created by Task 1)

**Context to load:**
- Spec BEH-4, BEH-5; Error Cases table (`ESCALATION_NOT_FOUND`)

- [ ] **Write failing test**

```python
# tests/test_escalations.py (append)
def test_get_escalation_by_number_returns_full_representation_with_null_fields(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", incident_number=None, owner=None)

    resp = client.get("/escalations/ESCALATION-0001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["number"] == "ESCALATION-0001"
    assert body["incident_number"] is None
    assert body["owner"] is None


def test_get_escalation_unknown_number_returns_404(client):
    resp = client.get("/escalations/ESCALATION-9999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "ESCALATION_NOT_FOUND"
    assert "ESCALATION-9999" in body["message"]
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_escalations.py::test_get_escalation_by_number_returns_full_representation_with_null_fields tests/test_escalations.py::test_get_escalation_unknown_number_returns_404`
Expected: FAIL — the unknown-number case gets FastAPI's default `{"detail": "Not Found"}` (no
`code` field, since no `/escalations/{number}` route exists yet), so
`body["code"] == "ESCALATION_NOT_FOUND"` raises `KeyError`; the known-number case gets a plain
`404 Not Found` with no body to parse as the expected representation.

- [ ] **Implement**

```python
# app/routers/escalations.py (append)
@router.get("/escalations/{number}", response_model=EscalationRead)
def get_escalation(number: str, request: Request):
    conn = request.app.state.db_conn
    row = conn.execute("SELECT * FROM escalations WHERE number = ?", (number,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Escalation {number} not found", "code": "ESCALATION_NOT_FOUND"},
        )
    return _row_to_escalation_read(row)
```

`/escalations` (Task 1) is declared before `/escalations/{number}` in the same router, so FastAPI
resolves `GET /escalations` to the list handler rather than treating `escalations` as a `{number}`
path value — no route-ordering conflict.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_escalations.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/escalations.py tests/test_escalations.py
git commit -m "feat(itsm-api): implement GET /escalations/{number} with 404 handling"
```

---

### Task 3: Implement `PATCH /escalations/{number}` [specialist: none]

**Charter capability:** List/get/update Escalations
**Depends on:** Task 2
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/escalations.py` — add partial-update endpoint
- Modify: `tests/test_escalations.py` — extend

**Tests:** `tests/test_escalations.py` (extend — BEH-6, BEH-7, BEH-8, plus SA-1's
`incident_number` immutability, SA-2's `closed_at: null` reopen, and the `MALFORMED_JSON` error
case; suite already created by Task 1)

**Context to load:**
- Spec BEH-6, BEH-7, BEH-8; Postconditions ("An Escalation's `number` and `account_id` never
  change"; "Setting `closed_at` to a non-null value removes that Escalation from subsequent
  `open_only=true` results"); Error Cases table (`ESCALATION_NOT_FOUND`, `MALFORMED_JSON`)
- Review notes: **SA-1** — `incident_number` structurally excluded from `EscalationPatch` (Task
  1), so this task's `UPDATE` has no path to write it regardless of request body content. **SA-2**
  — `closed_at` uses the identical `exclude_unset` mechanism as `owner`, so an explicit
  `closed_at: null` reopens the Escalation.
- Constitution Principle 6: the two ownerless seeded escalations are load-bearing —
  `owner: null` PATCH must succeed, not be rejected or silently defaulted to a placeholder.

- [ ] **Write failing test**

```python
# tests/test_escalations.py (append)
def test_patch_escalation_updates_summary_owner_and_closed_at(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", summary="old", owner=None, closed_at=None)

    resp = client.patch(
        "/escalations/ESCALATION-0001",
        json={"summary": "new summary", "owner": "dana", "closed_at": "2026-03-01T00:00:00Z"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == "new summary"
    assert body["owner"] == "dana"
    assert body["closed_at"] == "2026-03-01T00:00:00Z"


def test_patch_escalation_ignores_immutable_fields_including_incident_number(client):
    conn = client.app.state.db_conn
    seed_escalation(
        conn, number="ESCALATION-0001", incident_number=None,
        account_id="ACC-1", opened_at="2026-01-01T00:00:00Z",
    )

    resp = client.patch(
        "/escalations/ESCALATION-0001",
        json={
            "number": "ESCALATION-9999",
            "account_id": "ACC-2",
            "opened_at": "2020-01-01T00:00:00Z",
            "incident_number": "TICKET-000999",
            "summary": "updated",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["number"] == "ESCALATION-0001"
    assert body["account_id"] == "ACC-1"
    assert body["opened_at"] == "2026-01-01T00:00:00Z"
    assert body["incident_number"] is None
    assert body["summary"] == "updated"


def test_patch_escalation_can_unassign_owner_with_explicit_null(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", owner="dana")

    resp = client.patch("/escalations/ESCALATION-0001", json={"owner": None})
    assert resp.status_code == 200
    assert resp.json()["owner"] is None


def test_patch_escalation_can_reopen_with_explicit_null_closed_at(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", closed_at="2026-02-01T00:00:00Z")

    resp = client.patch("/escalations/ESCALATION-0001", json={"closed_at": None})
    assert resp.status_code == 200
    assert resp.json()["closed_at"] is None

    listing = client.get("/escalations?open_only=true").json()
    assert "ESCALATION-0001" in {item["number"] for item in listing["items"]}


def test_patch_escalation_unknown_number_returns_404(client):
    resp = client.patch("/escalations/ESCALATION-9999", json={"summary": "x"})
    assert resp.status_code == 404
    assert resp.json()["code"] == "ESCALATION_NOT_FOUND"


def test_patch_escalation_malformed_json_returns_400(client):
    resp = client.patch(
        "/escalations/ESCALATION-0001",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "MALFORMED_JSON"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_escalations.py`
Expected: FAIL — `405 Method Not Allowed` on every PATCH assertion (no `PATCH /escalations/{number}`
route registered yet).

- [ ] **Implement**

```python
# app/routers/escalations.py (append)
from app.models import EscalationPatch

_PATCHABLE_FIELDS = ("summary", "owner", "closed_at")


@router.patch("/escalations/{number}", response_model=EscalationRead)
def patch_escalation(number: str, payload: EscalationPatch, request: Request):
    conn = request.app.state.db_conn
    row = conn.execute("SELECT * FROM escalations WHERE number = ?", (number,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Escalation {number} not found", "code": "ESCALATION_NOT_FOUND"},
        )

    updates = payload.model_dump(exclude_unset=True)
    set_clauses = [f"{field} = ?" for field in _PATCHABLE_FIELDS if field in updates]
    values = [updates[field] for field in _PATCHABLE_FIELDS if field in updates]
    if set_clauses:
        conn.execute(
            f"UPDATE escalations SET {', '.join(set_clauses)} WHERE number = ?",
            (*values, number),
        )
        conn.commit()

    row = conn.execute("SELECT * FROM escalations WHERE number = ?", (number,)).fetchone()
    return _row_to_escalation_read(row)
```

`EscalationPatch` (Task 1) has no `number`, `account_id`, `opened_at`, or `incident_number`
field, so `payload.model_dump(exclude_unset=True)` can never contain those keys even if the raw
request JSON does. `_PATCHABLE_FIELDS` is a second, redundant guard: even if a future edit to
`EscalationPatch` accidentally added one of those fields, the `UPDATE`'s `SET` clause is still
built only from this fixed allow-list — the same two-layer structural pattern used for `id`/
`key`/`project_id` immutability in the sibling `mock-jira` repo's Issue PATCH. This closes SA-1:
`incident_number` is silently ignored identically to the three fields BEH-6 names explicitly.
`exclude_unset=True` is what makes `{"owner": null}` and `{"closed_at": null}` distinguishable
from "field omitted" — Pydantic tracks which fields were actually present in the parsed body, so
an explicit JSON `null` is included in the dict as `None` while an omitted field is absent
entirely. Both `owner` and `closed_at` go through the identical code path, so a
`{"closed_at": null}` PATCH reopens the Escalation exactly as a `{"owner": null}` PATCH unassigns
it — this closes SA-2 without a special case. Malformed JSON on `PATCH` raises
`RequestValidationError` with `type: json_invalid` before this handler body runs;
`incident-lifecycle.plan.md`'s (cross-plan) Task 1 `validation_exception_handler` already
special-cases that as `400 MALFORMED_JSON`, reused unchanged, and no row is read or written
(satisfies "persists no change" for that error path).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_escalations.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/escalations.py tests/test_escalations.py
git commit -m "feat(itsm-api): implement PATCH /escalations/{number} with structural immutable-field enforcement"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are
recorded in the validation report (`.validate.md`), not in this plan.

`governance/gates.yaml` exists and is used in place of the constitution's generic gate list:

- **Test Suite** (`test`, deterministic, required, severity error): `python3 -m pytest -q`
- **Linter** (`lint`, deterministic, required, severity error): `ruff check .`
- **Integration Tests** (`integration-test`, deterministic, required): command is unwired
  (`command: ""` in `gates.yaml`). This gate is **skipped** for this plan; nothing in this plan's
  task list requires an integration suite beyond the unit-level `TestClient` coverage above.
- All acceptance criteria from `escalations.spec.md` satisfied (BEH-1 through BEH-8).
