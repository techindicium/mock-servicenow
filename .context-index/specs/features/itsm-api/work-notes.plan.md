<!-- partial_schema: plan@1 -->

# Implementation Plan: Work notes list and add

> **Methodology:** adev
> **Charter:** .context-index/specs/features/itsm-api/charter.md
> **Spec:** .context-index/specs/features/itsm-api/work-notes.spec.md
> **Review:** PASS_WITH_NOTES (2026-09-07)
> **Platform:** FastAPI (per constitution's "follow mock-jira's shape"), Python 3.11, SQLite, Pydantic

**Goal:** Implement the WorkNote list/add HTTP surface (`GET /incidents/{number}/work_notes`,
`POST /incidents/{number}/work_notes`) with a server-assigned, collision-proof
`INTERACTION-NNNNNNN` `sys_id`, no authorship or business-rule guard on `POST` (constitution
Principle 5), and structural validation retained (`note_type` enum, required fields).

**Architecture (updated 2026-09-07 cross-plan consistency pass):** This plan was authored before
`incident-lifecycle.plan.md` existed; it has since been written and, per that pass, was designated
this charter's canonical foundation owner. `incident-lifecycle.plan.md`'s Task 1 already creates
`app/db.py` with `create_schema()` covering **all six** charter tables up front — including
`work_notes` — plus `app/models.py`, `app/errors.py`, `app/main.py`, `app/pagination.py`,
`requirements.txt`, and `tests/conftest.py` (the `client`/`conn` fixtures). Concretely, this means:
the `work_notes` table this plan's Task 1 below describes as "extending `create_schema()`" **already
exists** with an identical column list by the time this plan runs — no schema-definition work is
actually needed, only confirming the table matches (it does) before adding
`allocate_work_note_sys_id()` and this spec's own Pydantic models. WorkNote is structurally
dependent on Incident: `work_notes.incident_number` is a FK to `incidents.number`, and both `GET`
and `POST` on this spec's endpoints must look up the parent Incident by `number` before doing
anything else.

This plan follows the same layout `mock-jira`'s shipped `issue-lifecycle.plan.md` established
(FastAPI router per entity, thin Pydantic models, the `HTTPException(detail={"message", "code"})`
envelope consumed by `app/errors.py`'s generic handlers, already generalized in the foundation to
cover this spec's `note_type` enum): new Pydantic models (`WorkNoteCreate`, `WorkNoteRead`,
`WorkNoteListResponse`) extend `app/models.py`; a new `app/routers/work_notes.py` mirrors
`app/routers/incidents.py`'s structure; `app/main.py` is modified only to mount the new router.

**sys_id collision-avoidance (SA-1 fix, folded into Task 3 below):** the reviewed spec text states
the `INTERACTION-NNNNNNN` scheme but — unlike `incident-lifecycle.spec.md`'s BEH-5 ("guaranteed
not to collide with any seeded or previously created number") — never states a non-collision
guarantee for `sys_id`. This plan closes that gap in code, mirroring the Incident `number`
scheme's guarantee: `allocate_work_note_sys_id()` derives the next sequence number from
`MAX(existing sys_id sequence)` (across both seeded and previously created rows, since seed data
uses the identical `INTERACTION-NNNNNNN` format per the charter's Domain Model), and the insert
path retries on a primary-key `UNIQUE` constraint violation (a defensive backstop against a
race between concurrent requests) rather than ever silently overwriting or duplicating a `sys_id`.
This makes the guarantee structural (PK constraint) plus derivational (max+1), not a single point
of failure — the same two-layer pattern `issue-lifecycle.plan.md` used for `id`/`key` immutability.

**Pagination envelope (SA-2 advisory, resolved here):** this plan's `GET
/incidents/{number}/work_notes` uses query params `page` (default `1`, 1-indexed) and `page_size`
(default `50`, max `200`), response envelope `{"items": [...], "page": 1, "page_size": 50,
"total": N}` — this is exactly the shape `incident-lifecycle.plan.md`'s Task 1 later confirmed as
the charter's canonical pagination envelope, so no reconciliation is needed. Like `GET /incidents`
and `GET /sla`, this endpoint does its own SQL-level `LIMIT`/`OFFSET` pagination rather than
routing through the shared `app/pagination.py`'s `paginate_rows()` (that helper is for endpoints
that page an already-fetched, small, in-memory row list, e.g. `user-directory`'s two endpoints) —
both approaches produce the same envelope shape.

**Constitution Validation:** Checked every task's files/behavior against `Architecture
Boundaries`. No task adds a workspace-repo dependency, touches auth, or breaks an already-shipped
contract — `/incidents/{number}/work_notes` is a net-new endpoint family. `POST` deliberately adds
no authorship/permission guard, per Principle 5 (constitution Autonomous section explicitly
permits "adding new mock endpoints that extend the existing contract" without human approval).
`governance/boundaries.yaml` has no rules configured (`boundaries: []`), so no file-pattern flags
apply. No task in this plan is marked `[REQUIRES HUMAN APPROVAL]`.

---

## File Structure

**Create:**
- `app/routers/work_notes.py` — `GET /incidents/{number}/work_notes`,
  `POST /incidents/{number}/work_notes`
- `tests/test_work_notes.py` — BEH-1 through BEH-7 coverage

**Modify:**
- `app/db.py` — add an `allocate_work_note_sys_id()` helper (SA-1 fix); the `work_notes` table
  itself already exists in `create_schema()` (`incident-lifecycle.plan.md`'s Task 1, the charter's
  canonical foundation, defines all six charter tables up front, `work_notes` included, with the
  identical column list this plan needs) — no table-creation change is needed here
- `app/models.py` — add `WorkNoteCreate`, `WorkNoteRead`, `WorkNoteListResponse` Pydantic models
- `app/main.py` — include the new `work_notes` router; no change to existing exception-handler
  registration

**Reference (read, do not modify — most created by `incident-lifecycle.plan.md`'s Task 1, the
charter's canonical foundation; cross-plan dependency):**
- `app/routers/incidents.py` (shipped by `incident-lifecycle` plan) — pattern reference
  for router structure, `request.app.state.db_conn` access, `HTTPException(detail={"message",
  "code"})` shape, and how `INCIDENT_NOT_FOUND` is raised there (this plan's 404 path must match
  it verbatim so both endpoint families report the same error code/shape for the same condition)
- `app/errors.py` (shipped by `incident-lifecycle.plan.md`'s Task 1) — the generic handlers there
  are already generalized with a `literal_error` branch (needed by `incident-lifecycle`'s own
  `state`/`priority` enum validation) and reused unchanged for this spec's `note_type` — no change
  to `app/errors.py` is needed by this plan
- `tests/conftest.py` (shipped by `incident-lifecycle.plan.md`'s Task 1) — reuse the existing
  `client`/`conn` fixtures (isolated temp SQLite file + `TestClient`/connection per test, full
  six-table schema pre-applied) unchanged; this plan's tests still need a local helper that seeds
  one Incident row to attach WorkNotes to (see Task 1 Context — a local `_create_incident()` test
  helper in `tests/test_work_notes.py`, since `incident-lifecycle`'s own test suite doesn't export
  one)
- `app/pagination.py` (shipped by `incident-lifecycle.plan.md`'s Task 1) — not used directly by
  this plan; `GET /incidents/{number}/work_notes` does its own SQL-level pagination (see plan
  header's Pagination envelope note)
- `.context-index/specs/features/itsm-api/charter.md` — Capability Map, Domain Model, Invariants
- `CLAUDE.md` — constitution: "MCP tools stay unguarded", "HTTP contract is the boundary"
- `.context-index/governance/gates.yaml` — authoritative quality-gate commands

---

## Context Packets

> No `source-manifest.files[]` exists on this spec yet. This module has no ADRs, no samples, and
> no `orientation/architecture.md`. Context packets fall back to charter + spec + constitution +
> the sibling `incident-lifecycle` spec (and, once it exists, its plan/implementation) as a
> pattern reference, per Step 2's "no source-manifest" fallback. **Every task in this plan also
> needs `incident-lifecycle.spec.md`'s Domain Model / Preconditions for the Incident row shape
> its `GET`/existence-check queries against — that spec is read in full, not excerpted, for every
> task below.**

### Task 1 Context (foundation)
- Spec: Preconditions ("The `incident-lifecycle` spec's Incident table and endpoints exist");
  Postconditions ("A WorkNote's `sys_id` and `incident_number` never change once assigned")
- Charter: Domain Model → WorkNote entity full field list (`sys_id`, `incident_number`,
  `created_at`, `created_by`, `note_type`, `body`); Relationships ("Every WorkNote belongs to
  exactly one Incident"); Invariants
- Review notes: **SA-1** — this task implements the collision-avoidance fix (see plan Architecture
  section above)
- **Cross-plan dependency:** `incident-lifecycle.plan.md` Task 1 — the charter's canonical
  foundation. Its `create_schema()` already defines all six charter tables, `work_notes` included
  (identical column list to what this spec needs), so this task adds only
  `allocate_work_note_sys_id()` to `app/db.py`, not a new table. `app/models.py`, `app/errors.py`,
  `app/main.py`, `app/pagination.py`, `requirements.txt`, `tests/conftest.py` (`client`/`conn`
  fixtures) already exist; **do not begin this plan's Task 1 until that plan's Task 1 has landed.**
- Source files: `app/db.py`, `app/models.py` (full read — existing Incident models for
  naming-convention consistency)
- Boundary rules: `.context-index/governance/boundaries.yaml` — empty, no rules to apply
- Heuristics: none available for module `itsm-api` (`adev heuristics retrieve` returned
  `__NONE__`)

### Task 2 Context
- Spec: BEH-1; Postconditions ("Every WorkNote created via `POST` is immediately retrievable via
  a subsequent `GET`... no eventual consistency window")
- Charter: capability "List/add Work Notes"; Quality Attributes ("pagination is required on every
  list endpoint")
- Source files: `app/routers/incidents.py` (read — pattern for a `GET`-by-parent-id list
  endpoint, once shipped), `app/db.py`/`app/models.py` (from Task 1, full read)

### Task 3 Context
- Spec: BEH-2; Error Cases table (`INCIDENT_NOT_FOUND`)
- Charter: capability "List/add Work Notes"
- Source files: `app/routers/work_notes.py` (from Task 2, full read — extending)

### Task 4 Context
- Spec: BEH-3, BEH-4; Postconditions ("A WorkNote's `sys_id` and `incident_number` never change
  once assigned"); System Constitution Reference (Principle 5 — no authorship guard)
- Charter: Domain Model → `sys_id` example (`INTERACTION-0100001`)
- Review notes: **SA-1** (sys_id collision-avoidance, implemented in Task 1, exercised here)
- Source files: `app/routers/work_notes.py` (from Task 2-3, full read — extending), `app/db.py`'s
  `allocate_work_note_sys_id()` (from Task 1)

### Task 5 Context
- Spec: BEH-5, BEH-6, BEH-7; Error Cases table (`VALIDATION_ERROR`, `INCIDENT_NOT_FOUND`)
- Charter: Domain Model → `note_type` enum (`comment`, `work_note`, `state_change`,
  `proposal_sent`)
- Review notes: none outstanding for this task's scope
- Source files: `app/routers/work_notes.py` (from Task 2-4, full read — extending), `app/errors.py`
  (read — confirm the `literal_error` branch exists; if not, add it here since `note_type` is the
  first `Literal`-typed field this plan introduces and the spec's Error Cases table requires
  naming "the invalid value and its allowed values")

---

## Heuristics

No heuristics available for module `itsm-api` (`adev heuristics retrieve` returned `__NONE__`).
Section omitted from further reference per Step 2.

---

## Parallelization

- Group A (sequential): Task 1 → Task 2 → Task 3 → Task 4 → Task 5

All five tasks are sequential: Task 1 is the schema/model foundation every later task imports
from, and Tasks 2-5 all extend the same two files (`app/routers/work_notes.py`,
`tests/test_work_notes.py`), so no independent group exists in this plan.

**Depends on (cross-plan):** Task 1 depends on `incident-lifecycle.plan.md` Task 1 (the charter's
canonical foundation — `app/db.py`'s `create_schema()` already defines all six charter tables,
`work_notes` included; `app/models.py`, `app/errors.py`, `app/main.py`, `app/pagination.py`,
`requirements.txt`, `tests/conftest.py` already exist). This is a cross-plan dependency, and it
gates this entire plan (Tasks 1-5), not just Task 1 in isolation, since every task here queries or
FKs against `incidents`.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Add sys_id allocator and WorkNote Pydantic models | small | unit | *(cross-plan)* incident-lifecycle Task 1 | 0 create, 2 modify |
| 2 | Implement `GET /incidents/{number}/work_notes` — success path | medium | unit | Task 1 | 2 create, 1 modify |
| 3 | Implement `GET /incidents/{number}/work_notes` — unknown incident | small | unit | Task 2 | 0 create, 2 modify |
| 4 | Implement `POST /incidents/{number}/work_notes` — success, unguarded authorship | medium | unit | Task 3 | 0 create, 2 modify |
| 5 | Implement `POST /incidents/{number}/work_notes` — validation and 404 | small | unit | Task 4 | 0 create, 1 modify |

All tasks resolve to the `unit` strategy (source: fallback — no `test_strategy` in spec
frontmatter, no `test_strategies` entries in `manifest.yaml` matching these paths).

**Granularity:** `per-behavior` (source: manifest — `test_policy.granularity: per-behavior` in
`.context-index/manifest.yaml`). `tests/test_db.py` (created by `incident-lifecycle.plan.md`'s
Task 1, which already tests `work_notes` table creation) is extended once (this plan's Task 1,
covering only the new sys_id-allocation precondition — not table creation, already covered).
`tests/test_work_notes.py` is created once (Task 2, covering BEH-1) and extended three times
(Task 3 for BEH-2, Task 4 for BEH-3/BEH-4, Task 5 for BEH-5/BEH-6/BEH-7).

---

## Task Structure

### Task 1: Add sys_id allocator and WorkNote Pydantic models [specialist: none]

**Charter capability:** List/add Work Notes (foundation)
**Depends on:** *(cross-plan)* `incident-lifecycle.plan.md` Task 1 — the charter's canonical
foundation. Its `create_schema()` already defines the `work_notes` table (identical column list
to what this spec needs), among all six charter tables; `app/models.py`, `app/errors.py`,
`app/main.py`, `app/pagination.py`, `requirements.txt`, `tests/conftest.py` already exist.
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/db.py` — add `allocate_work_note_sys_id()` (the `work_notes` table itself already
  exists; no `create_schema()` change is needed)
- Modify: `app/models.py` — add `WorkNoteCreate`, `WorkNoteRead`, `WorkNoteListResponse`
- Test: `tests/test_db.py`

**Tests:** `tests/test_db.py` (extend — sys_id-allocation precondition only; the suite already
exists from `incident-lifecycle.plan.md`'s Task 1 and already tests `work_notes` table creation)

**Context to load:**
- Spec Preconditions and Postconditions (sys_id/incident_number immutability)
- Charter Domain Model: WorkNote entity (`sys_id`, `incident_number`, `created_at`, `created_by`,
  `note_type`, `body`)
- Review note **SA-1**: sys_id must carry an explicit non-collision guarantee, mirroring the
  Incident `number` scheme

- [ ] **Write failing test**

```python
# tests/test_db.py (append)
# `work_notes` table creation is already covered by incident-lifecycle.plan.md's Task 1
# (cross-plan) test_create_schema_creates_all_six_charter_tables — no need to re-test it here.


def test_allocate_work_note_sys_id_starts_at_interaction_0000001(tmp_path):
    from app.db import allocate_work_note_sys_id

    db_path = tmp_path / "test.db"
    conn = get_connection(str(db_path))
    create_schema(conn)

    assert allocate_work_note_sys_id(conn) == "INTERACTION-0000001"


def test_allocate_work_note_sys_id_continues_after_existing_rows(tmp_path):
    from app.db import allocate_work_note_sys_id

    db_path = tmp_path / "test.db"
    conn = get_connection(str(db_path))
    create_schema(conn)
    # Simulate seeded rows using the same INTERACTION-NNNNNNN scheme, out of order,
    # to prove the allocator derives from MAX(existing), not COUNT(rows).
    conn.execute(
        "INSERT INTO work_notes (sys_id, incident_number, created_by, note_type, body) "
        "VALUES ('INTERACTION-0100000', 'TICKET-000001', 'assist', 'comment', 'seeded')"
    )
    conn.commit()

    assert allocate_work_note_sys_id(conn) == "INTERACTION-0100001"


def test_allocate_work_note_sys_id_never_collides_across_calls(tmp_path):
    from app.db import allocate_work_note_sys_id

    db_path = tmp_path / "test.db"
    conn = get_connection(str(db_path))
    create_schema(conn)

    seen = set()
    for _ in range(25):
        sys_id = allocate_work_note_sys_id(conn)
        assert sys_id not in seen
        seen.add(sys_id)
        conn.execute(
            "INSERT INTO work_notes (sys_id, incident_number, created_by, note_type, body) "
            "VALUES (?, 'TICKET-000001', 'assist', 'comment', 'x')",
            (sys_id,),
        )
        conn.commit()
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_db.py`
Expected: FAIL — `ImportError: cannot import name 'allocate_work_note_sys_id'`, since it doesn't
exist yet. The `work_notes` table already exists (`incident-lifecycle.plan.md`'s Task 1), so
inserts against it in the tests above succeed once the function itself is defined.

- [ ] **Implement**

```python
# app/db.py (append — the work_notes table already exists from incident-lifecycle.plan.md's
# Task 1's create_schema(); this function is the only addition needed here)
def allocate_work_note_sys_id(conn: sqlite3.Connection) -> str:
    """Collision-proof INTERACTION-NNNNNNN allocation (SA-1 fix), mirroring the Incident
    `number` scheme's "guaranteed not to collide with any seeded or previously created
    number" guarantee.

    Derives the next sequence number from MAX(existing sys_id sequence) across both seeded
    and previously created rows (seed data uses the identical scheme), so it always continues
    past the highest number on disk rather than restarting at a count-based value. The
    `sys_id` PRIMARY KEY constraint is a second, independent backstop: if a concurrent insert
    claims the derived candidate between this read and the caller's write, the caller's
    INSERT raises sqlite3.IntegrityError and must re-call this function for a fresh candidate
    (see Task 4's insert-with-retry loop) rather than ever overwriting or duplicating a row.
    """
    row = conn.execute(
        "SELECT COALESCE(MAX(CAST(SUBSTR(sys_id, 12) AS INTEGER)), 0) AS max_seq "
        "FROM work_notes"
    ).fetchone()
    next_seq = row["max_seq"] + 1
    return f"INTERACTION-{next_seq:07d}"
```

```python
# app/models.py (append)
from typing import List, Literal

NOTE_TYPES = ("comment", "work_note", "state_change", "proposal_sent")


class WorkNoteCreate(BaseModel):
    created_by: str
    note_type: Literal["comment", "work_note", "state_change", "proposal_sent"]
    body: str


class WorkNoteRead(BaseModel):
    sys_id: str
    incident_number: str
    created_at: str
    created_by: str
    note_type: str
    body: str


class WorkNoteListResponse(BaseModel):
    items: List[WorkNoteRead]
    page: int
    page_size: int
    total: int
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_db.py`
Expected: PASS

- [ ] **Commit**

Branch: `feat/itsm-api/work-notes`

```bash
git add app/db.py app/models.py tests/test_db.py
git commit -m "feat(itsm-api): add WorkNote schema, collision-proof sys_id allocator, and WorkNote Pydantic models"
```

---

### Task 2: Implement `GET /incidents/{number}/work_notes` — success path [specialist: none]

**Charter capability:** List/add Work Notes
**Depends on:** Task 1
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `app/routers/work_notes.py`
- Modify: `app/main.py` — include the work_notes router
- Test: `tests/test_work_notes.py`

**Tests:** `tests/test_work_notes.py` (create — first task to touch this behavior; covers BEH-1)

**Context to load:**
- Spec BEH-1; Postconditions (no eventual consistency window)
- Charter Quality Attributes: pagination required on every list endpoint
- `app/routers/incidents.py` — pattern reference for `request.app.state.db_conn` access and
  `HTTPException(detail={"message", "code"})` shape (assumed shipped)

- [ ] **Write failing test**

```python
# tests/test_work_notes.py
def _create_incident(client, number="TICKET-000001"):
    # Assumes incident-lifecycle's POST /incidents exists; if incident numbers are
    # server-assigned rather than client-supplied by the time this plan is implemented,
    # replace this helper with a call to POST /incidents and capture the returned number.
    resp = client.post(
        "/incidents",
        json={
            "account_id": "ACCT-0001",
            "category": "network",
            "short_description": "Test incident",
            "description": "Created for work-notes test fixture",
            "state": "new",
            "priority": 3,
        },
    )
    return resp.json()["number"]


def test_list_work_notes_returns_paginated_chronological_items(client):
    number = _create_incident(client)
    client.post(
        f"/incidents/{number}/work_notes",
        json={"created_by": "customer", "note_type": "comment", "body": "First"},
    )
    client.post(
        f"/incidents/{number}/work_notes",
        json={"created_by": "assist", "note_type": "work_note", "body": "Second"},
    )
    resp = client.get(f"/incidents/{number}/work_notes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["total"] == 2
    assert [item["body"] for item in body["items"]] == ["First", "Second"]
```

Note: this test relies on `POST /incidents/{number}/work_notes` to seed rows, which does not
exist until Task 4 — this is a deliberate, temporary forward reference. To keep this task's RED
step meaningful and self-contained without Task 4's endpoint, insert rows directly via the test
DB connection instead:

```python
# tests/test_work_notes.py (revised — no forward reference to Task 4)
def test_list_work_notes_returns_paginated_chronological_items(client, conn):
    number = _create_incident(client)
    conn.execute(
        "INSERT INTO work_notes (sys_id, incident_number, created_at, created_by, note_type, body) "
        "VALUES ('INTERACTION-0000001', ?, '2026-09-07T10:00:00', 'customer', 'comment', 'First')",
        (number,),
    )
    conn.execute(
        "INSERT INTO work_notes (sys_id, incident_number, created_at, created_by, note_type, body) "
        "VALUES ('INTERACTION-0000002', ?, '2026-09-07T11:00:00', 'assist', 'work_note', 'Second')",
        (number,),
    )
    conn.commit()

    resp = client.get(f"/incidents/{number}/work_notes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["total"] == 2
    assert [item["body"] for item in body["items"]] == ["First", "Second"]
```

`tests/conftest.py`'s `conn` fixture (`incident-lifecycle.plan.md`'s Task 1) already exposes the
same connection `client`'s `TestClient` uses, for direct DB seeding.

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_work_notes.py`
Expected: FAIL — `404 Not Found` (no `/incidents/{number}/work_notes` route registered yet) or
`ModuleNotFoundError: No module named 'app.routers.work_notes'`.

- [ ] **Implement**

```python
# app/routers/work_notes.py
from fastapi import APIRouter, HTTPException, Query, Request

from app.models import WorkNoteListResponse, WorkNoteRead

router = APIRouter()


def _row_to_work_note_read(row) -> WorkNoteRead:
    return WorkNoteRead(
        sys_id=row["sys_id"],
        incident_number=row["incident_number"],
        created_at=row["created_at"],
        created_by=row["created_by"],
        note_type=row["note_type"],
        body=row["body"],
    )


@router.get(
    "/incidents/{number}/work_notes",
    response_model=WorkNoteListResponse,
)
def list_work_notes(
    number: str,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    conn = request.app.state.db_conn
    rows = conn.execute(
        "SELECT * FROM work_notes WHERE incident_number = ? "
        "ORDER BY created_at ASC, sys_id ASC "
        "LIMIT ? OFFSET ?",
        (number, page_size, (page - 1) * page_size),
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) AS c FROM work_notes WHERE incident_number = ?", (number,)
    ).fetchone()["c"]
    return WorkNoteListResponse(
        items=[_row_to_work_note_read(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
```

`ORDER BY created_at ASC, sys_id ASC` — a `sys_id` tie-breaker is required because
`created_at` has only second-level precision (`datetime('now')` in SQLite); two WorkNotes
created within the same second would otherwise have an undefined relative order, which would
make BEH-1's "ordered by `created_at` ascending" flaky under fast test execution. Since `sys_id`
is allocated monotonically (Task 1), sorting by it as a secondary key reproduces true creation
order even when timestamps tie.

Wire the router in `app/main.py`:

```python
# app/main.py (modify)
from app.routers.work_notes import router as work_notes_router

app.include_router(work_notes_router)
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_work_notes.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/work_notes.py app/main.py tests/test_work_notes.py
git commit -m "feat(itsm-api): implement GET /incidents/{number}/work_notes with pagination and chronological order"
```

---

### Task 3: Implement `GET /incidents/{number}/work_notes` — unknown incident [specialist: none]

**Charter capability:** List/add Work Notes
**Depends on:** Task 2
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/work_notes.py` — add existence check
- Modify: `tests/test_work_notes.py` — extend
- Test: `tests/test_work_notes.py`

**Tests:** `tests/test_work_notes.py` (extend — BEH-2; suite already created by Task 2)

**Context to load:**
- Spec BEH-2 and Error Cases table (`INCIDENT_NOT_FOUND`)
- `app/routers/incidents.py` — the exact `INCIDENT_NOT_FOUND` message/code shape used there
  (assumed shipped by `incident-lifecycle`), so both endpoint families report identically

- [ ] **Write failing test**

```python
# tests/test_work_notes.py (append)
def test_list_work_notes_unknown_incident_returns_404(client):
    resp = client.get("/incidents/TICKET-999999/work_notes")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "INCIDENT_NOT_FOUND"
    assert "TICKET-999999" in body["message"]
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_work_notes.py::test_list_work_notes_unknown_incident_returns_404`
Expected: FAIL — currently returns `200` with an empty `items` list instead of `404`, since the
handler never checks whether the Incident exists before querying WorkNotes.

- [ ] **Implement**

```python
# app/routers/work_notes.py (modify list_work_notes)
@router.get(
    "/incidents/{number}/work_notes",
    response_model=WorkNoteListResponse,
)
def list_work_notes(
    number: str,
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    conn = request.app.state.db_conn
    incident = conn.execute(
        "SELECT 1 FROM incidents WHERE number = ?", (number,)
    ).fetchone()
    if incident is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"Incident {number} not found",
                "code": "INCIDENT_NOT_FOUND",
            },
        )

    rows = conn.execute(
        "SELECT * FROM work_notes WHERE incident_number = ? "
        "ORDER BY created_at ASC, sys_id ASC "
        "LIMIT ? OFFSET ?",
        (number, page_size, (page - 1) * page_size),
    ).fetchall()
    total = conn.execute(
        "SELECT COUNT(*) AS c FROM work_notes WHERE incident_number = ?", (number,)
    ).fetchone()["c"]
    return WorkNoteListResponse(
        items=[_row_to_work_note_read(r) for r in rows],
        page=page,
        page_size=page_size,
        total=total,
    )
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_work_notes.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/work_notes.py tests/test_work_notes.py
git commit -m "feat(itsm-api): return 404 INCIDENT_NOT_FOUND from GET .../work_notes for an unknown incident"
```

---

### Task 4: Implement `POST /incidents/{number}/work_notes` — success, unguarded authorship [specialist: none]

**Charter capability:** List/add Work Notes
**Depends on:** Task 3
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/work_notes.py` — add create endpoint
- Modify: `tests/test_work_notes.py` — extend
- Test: `tests/test_work_notes.py`

**Tests:** `tests/test_work_notes.py` (extend — BEH-3, BEH-4; suite already created by Task 2)

**Context to load:**
- Spec BEH-3, BEH-4; Postconditions ("sys_id and incident_number never change once assigned");
  System Constitution Reference Principle 5 ("this HTTP layer never adds a write guard the MCP
  `add_work_note` tool intentionally omits")
- Review notes: **SA-1** — this task exercises `allocate_work_note_sys_id()` (Task 1) with a
  retry-on-collision insert loop, the second half of the SA-1 fix

- [ ] **Write failing test**

```python
# tests/test_work_notes.py (append)
def test_post_work_note_returns_201_with_server_assigned_sys_id(client):
    number = _create_incident(client)
    resp = client.post(
        f"/incidents/{number}/work_notes",
        json={"created_by": "assist", "note_type": "work_note", "body": "Investigating"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["sys_id"].startswith("INTERACTION-")
    assert body["incident_number"] == number
    assert body["created_by"] == "assist"
    assert body["note_type"] == "work_note"
    assert body["body"] == "Investigating"
    assert body["created_at"]  # server-assigned, non-empty


def test_post_work_note_is_immediately_retrievable_via_get(client):
    number = _create_incident(client)
    post_resp = client.post(
        f"/incidents/{number}/work_notes",
        json={"created_by": "customer", "note_type": "comment", "body": "Thanks!"},
    )
    sys_id = post_resp.json()["sys_id"]
    list_resp = client.get(f"/incidents/{number}/work_notes")
    assert sys_id in [item["sys_id"] for item in list_resp.json()["items"]]


def test_post_work_note_accepts_any_created_by_with_no_authorship_check(client):
    number = _create_incident(client)
    for author in ("customer", "some.random.agent.name", "assist"):
        resp = client.post(
            f"/incidents/{number}/work_notes",
            json={"created_by": author, "note_type": "comment", "body": "x"},
        )
        assert resp.status_code == 201
        assert resp.json()["created_by"] == author


def test_post_work_note_does_not_mutate_parent_incident(client):
    number = _create_incident(client)
    before = client.get(f"/incidents/{number}").json()
    client.post(
        f"/incidents/{number}/work_notes",
        json={"created_by": "assist", "note_type": "state_change", "body": "Marked resolved"},
    )
    after = client.get(f"/incidents/{number}").json()
    assert before == after
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_work_notes.py::test_post_work_note_returns_201_with_server_assigned_sys_id`
Expected: FAIL — `405 Method Not Allowed` (no `POST /incidents/{number}/work_notes` route yet).

- [ ] **Implement**

```python
# app/routers/work_notes.py (append)
import sqlite3

from app.db import allocate_work_note_sys_id
from app.models import WorkNoteCreate

_MAX_SYS_ID_RETRIES = 5


@router.post(
    "/incidents/{number}/work_notes",
    response_model=WorkNoteRead,
    status_code=201,
)
def create_work_note(number: str, payload: WorkNoteCreate, request: Request):
    conn = request.app.state.db_conn
    incident = conn.execute(
        "SELECT 1 FROM incidents WHERE number = ?", (number,)
    ).fetchone()
    if incident is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"Incident {number} not found",
                "code": "INCIDENT_NOT_FOUND",
            },
        )

    # No authorship/business-rule guard here — payload.created_by is trusted as-is, per
    # constitution Principle 5 and spec BEH-4. Structural validation (note_type enum,
    # required fields) is still enforced by Pydantic on WorkNoteCreate (Task 1/Task 5).
    last_error = None
    for _ in range(_MAX_SYS_ID_RETRIES):
        sys_id = allocate_work_note_sys_id(conn)
        try:
            conn.execute(
                "INSERT INTO work_notes "
                "(sys_id, incident_number, created_by, note_type, body) "
                "VALUES (?, ?, ?, ?, ?)",
                (sys_id, number, payload.created_by, payload.note_type, payload.body),
            )
            conn.commit()
            break
        except sqlite3.IntegrityError as exc:
            last_error = exc
            continue
    else:
        raise RuntimeError(
            f"Could not allocate a unique WorkNote sys_id after "
            f"{_MAX_SYS_ID_RETRIES} attempts"
        ) from last_error

    row = conn.execute("SELECT * FROM work_notes WHERE sys_id = ?", (sys_id,)).fetchone()
    return _row_to_work_note_read(row)
```

The retry loop is the second half of the SA-1 fix (see Task 1's docstring): `IntegrityError` on
the `sys_id` PRIMARY KEY is the only way two concurrent requests could ever collide, since
`allocate_work_note_sys_id()` always derives from `MAX(existing)`. On collision, the loop simply
re-derives a fresh candidate (which will now be `MAX+1` again, one higher than the row that just
won the race) and retries — it never overwrites, never skips a number silently, and never returns
a `sys_id` to the caller that wasn't actually the row inserted.

`test_post_work_note_does_not_mutate_parent_incident` exercises the spec's Postconditions clause
("Posting a WorkNote, including one with `note_type: state_change`, never mutates the parent
Incident's `state`") — this endpoint's implementation never touches the `incidents` table at all
beyond the read-only existence check, so this is a structural guarantee, not a runtime check.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_work_notes.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/work_notes.py tests/test_work_notes.py
git commit -m "feat(itsm-api): implement POST /incidents/{number}/work_notes with collision-proof sys_id and no authorship guard"
```

---

### Task 5: Implement `POST /incidents/{number}/work_notes` — validation and 404 [specialist: none]

**Charter capability:** List/add Work Notes
**Depends on:** Task 4
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Test: `tests/test_work_notes.py` — extend (no production code change expected; see below)

**Tests:** `tests/test_work_notes.py` (extend — BEH-5, BEH-6, BEH-7; suite already created by
Task 2)

**Context to load:**
- Spec BEH-5, BEH-6, BEH-7; Error Cases table (`VALIDATION_ERROR`, `INCIDENT_NOT_FOUND`)
- Charter Domain Model: `note_type` fixed values (`comment`, `work_note`, `state_change`,
  `proposal_sent`)

- [ ] **Write failing test**

```python
# tests/test_work_notes.py (append)
def test_post_work_note_invalid_note_type_returns_422(client):
    number = _create_incident(client)
    resp = client.post(
        f"/incidents/{number}/work_notes",
        json={"created_by": "assist", "note_type": "not_a_real_type", "body": "x"},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "note_type" in body["message"]
    # Error Cases table requires naming the allowed values, not just "field is required"
    for allowed in ("comment", "work_note", "state_change", "proposal_sent"):
        assert allowed in body["message"]

    list_resp = client.get(f"/incidents/{number}/work_notes")
    assert list_resp.json()["total"] == 0


def test_post_work_note_unknown_incident_returns_404_and_creates_nothing(client):
    resp = client.post(
        "/incidents/TICKET-999999/work_notes",
        json={"created_by": "assist", "note_type": "comment", "body": "x"},
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "INCIDENT_NOT_FOUND"
    assert "TICKET-999999" in body["message"]


def test_post_work_note_missing_required_field_returns_422(client):
    number = _create_incident(client)
    resp = client.post(
        f"/incidents/{number}/work_notes",
        json={"created_by": "assist", "note_type": "comment"},  # body missing
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "body" in body["message"]

    list_resp = client.get(f"/incidents/{number}/work_notes")
    assert list_resp.json()["total"] == 0
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_work_notes.py::test_post_work_note_invalid_note_type_returns_422`
Expected: PASS immediately, no code change needed — `incident-lifecycle.plan.md`'s (cross-plan)
Task 1 `validation_exception_handler` already has the `literal_error` branch (needed there for
`state`/`priority`), and it is generic across every `Literal`-typed field project-wide, so
`note_type`'s invalid-value message is satisfied by the same code path with no Work-Note-specific
change to `app/errors.py`. This step exists to prove the assertion is a genuine, tested
consequence of the shared foundation and this plan's `WorkNoteCreate` model (Task 1), per this
plan's TDD discipline, not to fix a gap.

- [ ] **Implement**

No implementation change. If the "Verify test fails" step above surfaces an unexpected failure,
fix it in `app/errors.py` here and re-run; this task's own code-change budget covers exactly and
only that contingency.

`test_post_work_note_missing_required_field_returns_422` needs no implementation change either:
`body` is a required (non-`Optional`) field on `WorkNoteCreate` (Task 1), so FastAPI/Pydantic
already raises `RequestValidationError` with `type: "missing"` before `create_work_note`'s body
ever runs, hitting the handler's existing fallback branch (`"{field} is required"`), which already
contains `"body"`. `test_post_work_note_unknown_incident_returns_404_and_creates_nothing` needs no
implementation change either — Task 4's existence check already runs before any insert is
attempted.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_work_notes.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests/test_work_notes.py
git commit -m "test(itsm-api): verify note_type enum validation and 404/422 no-op guarantees on POST work_notes"
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
- All acceptance criteria from `work-notes.spec.md` satisfied (BEH-1 through BEH-7), including
  the postcondition that posting a WorkNote never mutates the parent Incident.
- **Pre-condition gate (not in `gates.yaml`, enforced manually before Task 1 begins):** the
  `incidents` table must exist in `app/db.py`'s `create_schema()` — this plan's implementer must
  confirm `incident-lifecycle.plan.md` has landed its foundation task (or manually verify the
  table exists) before starting Task 1.
