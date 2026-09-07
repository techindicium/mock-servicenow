<!-- partial_schema: plan@1 -->

# Implementation Plan: Incident lifecycle CRUD

> **Methodology:** adev
> **Charter:** .context-index/specs/features/itsm-api/charter.md
> **Spec:** .context-index/specs/features/itsm-api/incident-lifecycle.spec.md
> **Review:** PASS_WITH_NOTES (2026-09-07)
> **Platform:** FastAPI 0.x (net-new scaffold), Python 3.11, SQLite, Pydantic, pytest, ruff

**Goal:** Stand up the Incident CRUD HTTP surface (`GET /incidents`, `GET /incidents/{number}`,
`POST /incidents`, `PATCH /incidents/{number}`) as the first code this repo has ever shipped,
scaffolding the FastAPI app itself alongside the Incident table and endpoints.

**Architecture:** This repo is greenfield — no `app/` directory exists yet. Per the constitution's
"Patterns to Follow" ("Follow `mock-jira`'s shape ... since this repo is built to the same
convention"), this plan scaffolds the identical layout: `app/db.py` (connection + schema),
`app/models.py` (Pydantic request/response models), `app/errors.py` (exception handlers producing
the structured `{"message", "code"}` error envelope the constitution's Coding Standards require),
`app/main.py` (app factory + router mounting), `app/pagination.py` (the shared pagination
helper — see SA-3 below), and `app/routers/incidents.py` (the endpoint family this spec defines).
Task 1 lays the foundation (schema + models + error envelope + app factory); Tasks 2-5 build one
endpoint each, in the spec's own BEH-1..BEH-9 order (GET list, GET by number, POST, PATCH), each
extending `app/routers/incidents.py` and `tests/test_incidents.py` rather than replacing them.

**Task 1 is this charter's canonical foundation, not just this spec's.** Four sibling plans in
this charter (`work-notes`, `escalations`, `sla-records`, `user-directory`, plus
`fixture-seeding`'s reliance on the same `conn` fixture) were each authored independently and in
parallel, without visibility into one another, and each originally invented its own copy of
`app/db.py`, `app/models.py`, `app/errors.py`, `app/main.py`, `requirements.txt`, and
`tests/conftest.py`. A cross-plan consistency pass (2026-09-07) designated this plan's Task 1 as
the single owner of all of those files, since this spec is the charter's primary capability
(BEH-1 through BEH-9, the richest spec) and `work-notes.plan.md` had already named it as the
dependency it needed. Concretely, Task 1 below now creates `app/db.py::create_schema()` covering
**all six** tables this charter defines (`incidents`, `work_notes`, `escalations`, `task_sla`,
`sys_user`, `assignment_group`) — not just `incidents` — because every sibling plan's tests depend
on `tests/conftest.py`'s `conn`/`client` fixtures having the full schema pre-applied from the
first test onward, before any sibling plan's own router work begins. `app/models.py` still holds
only this spec's own `Incident*` models; each sibling plan's own Task 1 now **extends** (modifies,
never recreates) `app/models.py` with its own entity's models, the same way it extends
`create_schema()`. `app/errors.py`'s handlers are written generically (see Task 1's
`validation_exception_handler`) so every sibling plan's own `Literal`-typed/`bool`-typed
query/body fields are covered without any sibling needing to touch this file. A minimal `GET /`
health route is included in `app/main.py` — not part of this spec's own BEH list, but required
infrastructure: `escalations.plan.md` and `sla-records.plan.md` both originally built one in their
own now-removed foundation tasks, and `api-e2e.plan.md`'s real-server-process fixture polls it to
detect a healthy startup. Building it once, here, is not scope creep against "every task traces to
a charter capability" — it is the same category of foundational, non-behavioral infrastructure as
the SQLite connection factory itself.

**Constitution Validation (Step 3):** Checked every task's files/behavior against `Architecture
Boundaries`. No task adds a workspace-repo dependency, touches auth, or breaks an existing
contract (there is no existing contract yet — this is the first HTTP surface built). No task adds
a permission or business-rule guard to `PATCH /incidents/{number}` — BEH-8 and constitution
Non-Negotiable Principle 5 both require it stay unguarded, and no task below adds one.
`governance/boundaries.yaml` has no rules configured (`boundaries: []`), so no file-pattern flags
apply. No task is marked `[REQUIRES HUMAN APPROVAL]`. `requirements.txt` is created fresh in Task
1 (`fastapi`, `uvicorn[standard]`, `pydantic`, `pytest`, `httpx`, `ruff`) — the same dependency set
`mock-jira` uses, per the constitution's explicit shape guidance.

**Review notes carried forward (PASS_WITH_NOTES):**
- **SA-1** (creation defaults for `opened_at`/`assignment_group` unspecified) — Task 4 makes this
  concrete: `opened_at` is **server-assigned** at creation time (never a client-supplied field —
  `IncidentCreate` has no `opened_at` field at all, so there is no path for a client to set it) and
  `assignment_group` **defaults to `null`** when omitted, exactly like `assigned_to` and
  `resolved_at`. `number` is likewise always server-assigned (`TICKET-NNNNNN`), never client input.
- **SA-2** (filter-value validation gap for `state`/`category`/`escalated`) — Task 2 makes this
  concrete: `state` is a closed enum (`new`/`in_progress`/`on_hold`/`resolved`/`closed`) — an
  unrecognized `state` filter value returns `422 VALIDATION_ERROR` naming the field and its
  allowed values, the same treatment BEH-7 gives an invalid `state` on write. `escalated` accepts
  only `true`/`false` (case-insensitive) — anything else returns the same `422 VALIDATION_ERROR`.
  `category` has **no closed enum** anywhere in the charter's Domain Model (unlike `state`/
  `priority`) — it is free text, so an unrecognized `category` filter value is not an error; it
  simply matches zero rows. This asymmetry (validated `state`/`escalated`, unvalidated `category`)
  is a deliberate design decision made once, here, documented in Task 2, not a residual gap.
- **SA-3** (pagination contract shape unspecified) — Task 2 defines the concrete envelope, since
  `GET /incidents` is this charter's largest, most-exercised endpoint (1,307+ rows) and this
  decision needs to be made exactly once:
  ```json
  {"items": [ {"number": "TICKET-000001", "...": "..."} ], "page": 1, "page_size": 50, "total": 1307}
  ```
  `page` (default `1`) and `page_size` (default `50`) are query parameters; `total` is the
  unpaginated count of rows matching the given filters. Every later list endpoint in this charter
  (work notes, escalations, SLA, users, assignment groups) reuses this exact envelope shape for
  consistency. Task 1 now also creates `app/pagination.py` — a `PageParams` FastAPI-`Depends`-able
  class (`page: int = Query(1, ge=1)`, `page_size: int = Query(50, ge=1, le=200)`) plus a
  `paginate_rows(rows, page, page_size)` helper for endpoints that page an already-fetched, small,
  in-memory row list (as `user-directory`'s two endpoints do) rather than pushing `LIMIT`/`OFFSET`
  into SQL. `GET /incidents` (Task 2 below) is high-cardinality enough (1,307+ rows) that it keeps
  doing its own SQL-level `LIMIT ? OFFSET ?` pagination rather than fetching every row and calling
  `paginate_rows()` — both approaches produce byte-identical `{"items", "page", "page_size",
  "total"}` envelopes, so this is a performance choice, not a shape divergence. This reconciles
  what were previously three independently-invented, slightly different pagination
  implementations (`user-directory.plan.md`'s original `app/pagination.py`,
  `escalations.plan.md`'s and `sla-records.plan.md`'s inline query params) onto one shared module.

---

## File Structure

**Create (canonical foundation — see Architecture note above; the entries marked "shared" below
are the cross-plan foundation every sibling `itsm-api` plan extends, not files scoped to this
spec alone):**
- `requirements.txt` *(shared)* — `fastapi`, `uvicorn[standard]`, `pydantic`, `pytest`, `httpx`,
  `ruff`
- `app/__init__.py` *(shared)* — empty package marker
- `app/db.py` *(shared)* — `get_connection()`, `create_schema()` (creates **all six** tables:
  `incidents`, `work_notes`, `escalations`, `task_sla`, `sys_user`, `assignment_group`),
  `next_incident_number()` (Incident-specific)
- `app/models.py` *(shared file, Incident-only models in this task)* — `IncidentCreate`,
  `IncidentRead`, `IncidentPatch`, `IncidentPage`; each sibling plan's own Task adds its own
  entity's models here by extending this file
- `app/errors.py` *(shared)* — exception handlers producing the `{"message", "code"}` error
  envelope, generalized to handle `literal_error` (invalid enum value), `bool_parsing`/`bool_type`
  (invalid boolean query param), and `json_invalid` (malformed request body), so no sibling plan
  needs to modify this file for its own enum/boolean fields
- `app/main.py` *(shared)* — `create_app()` factory; wires db connection into `app.state.db_conn`,
  registers exception handlers, exposes `GET /` health check; router mounting for
  `app/routers/incidents.py` added in Task 2 (sibling plans mount their own routers in their own
  tasks)
- `app/pagination.py` *(shared)* — `PageParams` (FastAPI `Depends`-able page/page_size query
  params) and `paginate_rows(rows, page, page_size)` for small, in-memory-paged list endpoints
- `app/routers/__init__.py` — empty package marker
- `app/routers/incidents.py` — `GET /incidents`, `GET /incidents/{number}`, `POST /incidents`,
  `PATCH /incidents/{number}`
- `tests/__init__.py` *(shared)* — empty package marker
- `tests/conftest.py` *(shared)* — `client` fixture: isolated temp SQLite file + `TestClient` per
  test (full six-table schema pre-applied via `create_app`); `conn` fixture exposing that same
  connection (`client.app.state.db_conn`) for direct fixture-row insertion, which every sibling
  plan's own tests and `fixture-seeding.plan.md` rely on
- `tests/test_db.py` — schema (all six tables) + number-generation coverage
- `tests/test_incidents.py` — BEH-1 through BEH-9 coverage

**Modify:** none — every file above is net-new (greenfield repo).

**Reference (read, do not modify):**
- `/Users/dpavancini/Development/adev-course/mock-jira/app/db.py`,
  `app/main.py`, `app/errors.py`, `app/routers/issues.py`, `tests/conftest.py` — the constitution's
  Coding Standards explicitly direct following this repo's shape (FastAPI over SQLite, thin
  routers, `HTTPException(detail={"message", "code"})` error envelope, per-test isolated SQLite
  file). Read these for pattern, not for reuse — no cross-repo import ever happens (Non-Negotiable
  Principle 1: no inbound dependencies).
- `.context-index/specs/features/itsm-api/charter.md` — Capability Map, Domain Model, Invariants
- `CLAUDE.md` — constitution: "the MCP tools stay unguarded" (Principle 5), "the HTTP contract is
  the boundary" (Principle 4)
- `.context-index/governance/gates.yaml` — authoritative quality-gate commands
- `PRD.md` — `incident` table field list (referenced by the charter's Domain Model)

---

## Context Packets

> No `source-manifest.files[]` exists on this spec (greenfield — no code yet). This module has no
> ADRs, no samples, and no `orientation/architecture.md`. Context packets fall back to charter +
> spec + constitution + `mock-jira`'s shipped source as a pattern reference (per the constitution's
> explicit "follow mock-jira's shape" directive), per Step 2's "no source-manifest" fallback.

### Task 1 Context
- Spec: Preconditions ("The API process is running and its SQLite database is available.")
- Charter: Domain Model → Incident entity full field list (`number`, `account_id`, `category`,
  `short_description`, `description`, `state`, `priority`, `opened_at`, `resolved_at`,
  `assigned_to`, `assignment_group`, `escalated`); Invariants — `state` closed to five values,
  `priority` integer 1-4, `number` stable and never renumbered; Domain Model entries for
  WorkNote, Escalation, TaskSla, SysUser, AssignmentGroup (needed only for their table's column
  list in `create_schema()` — their own Pydantic models and endpoints are each sibling plan's own
  responsibility, not this task's)
- Constitution: Coding Standards → Error handling ("fail at the HTTP boundary with a real,
  structured error response, not a generic 500")
- Pattern reference: `mock-jira/app/db.py`, `app/models.py`, `app/errors.py`, `app/main.py`,
  `tests/conftest.py` (full read — this task's scaffold mirrors their shape)
- Boundary rules: `.context-index/governance/boundaries.yaml` — empty, no rules to apply
- Heuristics: none available for module `itsm-api`
- Cross-plan: this task is the canonical foundation `work-notes.plan.md`, `escalations.plan.md`,
  `sla-records.plan.md`, and `user-directory.plan.md` each depend on (see plan header's
  Architecture note) — their own Task 1s were rewritten during the 2026-09-07 consistency pass to
  extend, not recreate, the files this task creates

### Task 2 Context
- Spec: BEH-1, BEH-2; Error Cases table (invalid `opened_after`/`opened_before` →
  `VALIDATION_ERROR`); review notes SA-2 (filter validation) and SA-3 (pagination envelope) — both
  resolved concretely in this task, see plan header
- Charter: capability "List/get Incident"; Quality Attributes ("pagination is required on every
  list endpoint")
- Pattern reference: `mock-jira/app/routers/issues.py` (list endpoint with filters — full read)
- Source files: `app/db.py`, `app/models.py`, `app/errors.py`, `app/main.py` (from Task 1, full
  read)

### Task 3 Context
- Spec: BEH-3, BEH-4; Error Cases table (`INCIDENT_NOT_FOUND`)
- Charter: capability "List/get Incident"
- Source files: `app/routers/incidents.py` (from Task 2, full read — extending, not replacing)

### Task 4 Context
- Spec: BEH-5, BEH-6, BEH-7 (create half); Error Cases table (`VALIDATION_ERROR`,
  `MALFORMED_JSON`); review note SA-1 (creation defaults) — resolved concretely in this task
- Charter: capability "Create/update Incident"; Invariants — `number` never reused, `state`/
  `priority` closed sets
- Pattern reference: `mock-jira/app/routers/issues.py::create_issue`,
  `mock-jira/app/errors.py::validation_exception_handler` (the `literal_error` branch — full read)
- Source files: `app/routers/incidents.py` (from Task 2-3, full read — extending)

### Task 5 Context
- Spec: BEH-7 (patch half), BEH-8, BEH-9; Postconditions ("`number` never changes once
  assigned"); Error Cases table (`INCIDENT_NOT_FOUND`, `VALIDATION_ERROR`)
- Charter: capability "Create/update Incident"; constitution Non-Negotiable Principle 5 ("the MCP
  tools stay unguarded" — this spec's Preconditions explicitly extend that to this HTTP layer:
  no permission/business-rule guard on `PATCH`, structural validation only)
- Pattern reference: `mock-jira/app/routers/issues.py::patch_issue` (structural immutability via
  a Pydantic model with no `id`/`key`/`project_id` field — full read)
- Source files: `app/routers/incidents.py` (from Task 2-4, full read — extending)

---

## Heuristics

No heuristics available for module `itsm-api` (`adev heuristics retrieve` returned `__NONE__`).
Section omitted from further reference per Step 2.

---

## Parallelization

- Group A (sequential): Task 1 → Task 2 → Task 3 → Task 4 → Task 5

All five tasks are sequential: Task 1 is the schema/model/app-factory foundation every later task
imports from and runs against, and Tasks 2-5 all extend the same two files
(`app/routers/incidents.py`, `tests/test_incidents.py`), so no independent group exists in this
plan.

**Cross-plan (downstream consumers):** `work-notes.plan.md`'s Task 1, `escalations.plan.md`'s
Task 1, `sla-records.plan.md`'s Task 1, and `user-directory.plan.md`'s Task 1 all depend on this
plan's Task 1 (foundation) rather than on any later task here — they extend `app/db.py`,
`app/models.py`, and `tests/conftest.py` once this task has created them, and each can start as
soon as this task lands, independently of Tasks 2-5. `fixture-seeding.plan.md` and
`api-e2e.plan.md` additionally depend on all four of those sibling plans' own table-creation work,
not just this one.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Bootstrap app scaffold (charter-wide foundation, all six tables), Incident table, and Pydantic models | medium | unit | — | 10 create, 0 modify |
| 2 | Implement `GET /incidents` with filters and pagination | medium | unit | Task 1 | 0 create, 2 modify |
| 3 | Implement `GET /incidents/{number}` | small | unit | Task 2 | 0 create, 2 modify |
| 4 | Implement `POST /incidents` | medium | unit | Task 3 | 0 create, 2 modify |
| 5 | Implement `PATCH /incidents/{number}` | medium | unit | Task 4 | 0 create, 2 modify |

All tasks resolve to the `unit` strategy (source: fallback — no `test_strategy` in spec
frontmatter, no `test_strategies` entries in `manifest.yaml` matching these paths). Per Step 5,
the Strategy Summary section is omitted since every task is `unit`.

**Granularity:** `per-behavior` (source: manifest — `test_policy.granularity: per-behavior` in
`.context-index/manifest.yaml`). `tests/test_db.py` is created once (Task 1, covering the
schema/number-generation precondition). `tests/test_incidents.py` is created once (Task 2,
covering BEH-1/BEH-2) and extended three times (Task 3 for BEH-3/BEH-4, Task 4 for
BEH-5/BEH-6/BEH-7-create-half, Task 5 for BEH-7-patch-half/BEH-8/BEH-9).

---

## Task Structure

### Task 1: Bootstrap app scaffold (charter-wide foundation), Incident table, and Pydantic models [specialist: none]

**Charter capability:** List/get Incident (foundation); also the canonical foundation for the
whole `itsm-api` charter — see plan header Architecture note.
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `requirements.txt`, `app/__init__.py`, `app/db.py`, `app/models.py`, `app/errors.py`,
  `app/main.py`, `app/pagination.py`, `app/routers/__init__.py`, `tests/__init__.py`,
  `tests/conftest.py`
- Test: `tests/test_db.py`

**Tests:** `tests/test_db.py` (create — schema and number-generation precondition; no BEH maps
directly to this file since it tests infrastructure the spec's Preconditions assume, not a
numbered Behavior)

**Context to load:**
- Charter Domain Model: Incident entity full field list; Invariants: `state` closed to five
  values, `priority` integer 1-4, `number` stable and `TICKET-NNNNNN`-shaped
- Constitution Coding Standards: structured error envelope requirement
- `mock-jira/app/db.py`, `app/models.py`, `app/errors.py`, `app/main.py`, `tests/conftest.py`
  (full read, pattern reference)

- [ ] **Write failing test**

```python
# tests/test_db.py
from app.db import create_schema, get_connection, next_incident_number

_ALL_TABLES = (
    "incidents", "work_notes", "escalations", "task_sla", "sys_user", "assignment_group",
)


def test_create_schema_creates_incidents_table(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='incidents'"
    ).fetchone()
    assert row is not None


def test_create_schema_creates_all_six_charter_tables(tmp_path):
    # This is the charter-wide foundation (see plan header): every sibling itsm-api plan's
    # tests/conftest.py `conn`/`client` fixture depends on the full schema being present from
    # the first test onward, not just the incidents table this spec itself owns.
    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    existing = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    for table in _ALL_TABLES:
        assert table in existing


def test_next_incident_number_starts_at_ticket_000001(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    assert next_incident_number(conn) == "TICKET-000001"


def test_next_incident_number_never_collides_with_existing_rows(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    conn.execute(
        """
        INSERT INTO incidents
            (number, account_id, category, short_description, description, state,
             priority, opened_at, escalated)
        VALUES ('TICKET-000005', 'ACC-1', 'network', 'x', 'x', 'new', 1, '2026-01-01T00:00:00Z', 0)
        """
    )
    conn.commit()
    assert next_incident_number(conn) == "TICKET-000006"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_db.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'` or `ImportError`, since none of
`app/db.py`'s functions exist yet.

- [ ] **Implement**

```python
# app/db.py
import re
import sqlite3

_NUMBER_RE = re.compile(r"^TICKET-(\d{6})$")


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Creates all six tables this charter's Domain Model defines. Only `incidents` is this
    spec's own responsibility; the other five (`work_notes`, `escalations`, `task_sla`,
    `sys_user`, `assignment_group`) are created here, up front, because every sibling
    itsm-api plan's tests/conftest.py `conn`/`client` fixture needs the full schema pre-applied
    from the first test onward — see plan header's Architecture note on this being the
    charter-wide canonical foundation. `CREATE TABLE IF NOT EXISTS` makes every statement
    additive and order-independent, so no sibling plan needs to touch this function's
    `incidents` statement, and this statement never needs to know about a sibling's rows."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            number TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            category TEXT NOT NULL,
            short_description TEXT NOT NULL,
            description TEXT NOT NULL,
            state TEXT NOT NULL,
            priority INTEGER NOT NULL,
            opened_at TEXT NOT NULL,
            resolved_at TEXT,
            assigned_to TEXT,
            assignment_group TEXT,
            escalated INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS work_notes (
            sys_id TEXT PRIMARY KEY,
            incident_number TEXT NOT NULL REFERENCES incidents(number),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL,
            note_type TEXT NOT NULL,
            body TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS escalations (
            number TEXT PRIMARY KEY,
            incident_number TEXT,
            account_id TEXT NOT NULL,
            summary TEXT NOT NULL,
            opened_at TEXT NOT NULL,
            closed_at TEXT,
            owner TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_sla (
            sys_id TEXT PRIMARY KEY,
            incident_number TEXT NOT NULL,
            sla_definition TEXT NOT NULL,
            target_minutes INTEGER NOT NULL,
            actual_minutes INTEGER,
            has_breached INTEGER NOT NULL,
            business_time_only INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS assignment_group (
            name TEXT PRIMARY KEY
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sys_user (
            name TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            assignment_group TEXT REFERENCES assignment_group(name)
        )
        """
    )
    conn.commit()


def next_incident_number(conn: sqlite3.Connection) -> str:
    """Server-assigned, TICKET-NNNNNN, guaranteed not to collide with any existing row
    (seeded or previously created) — derived from the current max suffix, not a separate
    counter table, so it stays correct even once the fixture-seeding spec lands rows directly."""
    max_seq = 0
    for row in conn.execute("SELECT number FROM incidents"):
        match = _NUMBER_RE.match(row["number"])
        if match:
            max_seq = max(max_seq, int(match.group(1)))
    return f"TICKET-{max_seq + 1:06d}"
```

```python
# app/models.py
# Charter-wide foundation file (see plan header): this task defines only the Incident models
# below. Each sibling itsm-api plan's own Task 1 (work-notes, escalations, sla-records,
# user-directory) appends its own entity's models to this same file — extending it, never
# recreating it.
from typing import Literal

from pydantic import BaseModel

INCIDENT_STATES = ("new", "in_progress", "on_hold", "resolved", "closed")


class IncidentCreate(BaseModel):
    account_id: str
    category: str
    short_description: str
    description: str
    state: Literal["new", "in_progress", "on_hold", "resolved", "closed"]
    priority: Literal[1, 2, 3, 4]
    escalated: bool = False
    resolved_at: str | None = None
    assigned_to: str | None = None
    assignment_group: str | None = None


class IncidentRead(BaseModel):
    number: str
    account_id: str
    category: str
    short_description: str
    description: str
    state: str
    priority: int
    opened_at: str
    resolved_at: str | None
    assigned_to: str | None
    assignment_group: str | None
    escalated: bool


class IncidentPatch(BaseModel):
    # Deliberately no `number`, `account_id`, or `opened_at` field — this is the structural
    # enforcement of those three being immutable (see Task 5): Pydantic drops unknown extra
    # keys silently, so there is no path for them to reach the UPDATE statement.
    state: Literal["new", "in_progress", "on_hold", "resolved", "closed"] | None = None
    priority: Literal[1, 2, 3, 4] | None = None
    assigned_to: str | None = None
    assignment_group: str | None = None


class IncidentPage(BaseModel):
    items: list[IncidentRead]
    page: int
    page_size: int
    total: int
```

```python
# app/errors.py
# Charter-wide foundation file (see plan header). Generalized so no sibling plan needs to modify
# this file for its own Literal-typed (enum) or bool-typed query/body fields: the `literal_error`
# branch handles every enum (Incident `state`/`priority`, WorkNote `note_type`, TaskSla
# `sla_definition`); the `bool_parsing`/`bool_type` branch handles every boolean query parameter
# (Incident/Escalation `escalated`/`open_only`, SLA `breached`); `field` is read from `loc[-1]`,
# which resolves correctly whether the error came from a request body field or a query parameter.
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "message" in detail and "code" in detail:
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code, content={"message": str(detail), "code": "ERROR"}
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    for error in errors:
        if error.get("type") == "json_invalid":
            return JSONResponse(
                status_code=400,
                content={"message": "Request body is not valid JSON", "code": "MALFORMED_JSON"},
            )
    first = errors[0] if errors else {}
    field = str(first.get("loc", ["field"])[-1])
    error_type = first.get("type")
    if error_type == "literal_error":
        allowed = first.get("ctx", {}).get("expected", "")
        return JSONResponse(
            status_code=422,
            content={"message": f"{field} must be one of: {allowed}", "code": "VALIDATION_ERROR"},
        )
    if error_type in ("bool_parsing", "bool_type"):
        return JSONResponse(
            status_code=422,
            content={
                "message": f"{field} must be a valid boolean (true or false)",
                "code": "VALIDATION_ERROR",
            },
        )
    return JSONResponse(
        status_code=422,
        content={"message": f"{field} is required", "code": "VALIDATION_ERROR"},
    )
```

```python
# app/main.py
# Charter-wide foundation file (see plan header). This task mounts only the incidents router;
# each sibling plan's own task adds `app.include_router(...)` for its own router here, in its own
# task, extending this file rather than recreating it.
import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.db import create_schema, get_connection
from app.errors import http_exception_handler, validation_exception_handler


def create_app(db_path: str) -> FastAPI:
    app = FastAPI(title="mock-servicenow itsm-api")
    conn = get_connection(db_path)
    create_schema(conn)
    app.state.db_conn = conn

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    @app.get("/")
    def health():
        # Not part of this spec's own BEH list, but required charter-wide infrastructure:
        # api-e2e.plan.md's `start_itsm_api()` fixture polls this route to detect a healthy
        # process startup, and mirrors mock-jira's equivalent health route.
        return {"status": "ok", "service": "mock-servicenow"}

    return app


# `DATABASE_PATH` env var override (default "servicenow.db") is what lets
# api-e2e.plan.md's `start_itsm_api()` fixture launch `uvicorn app.main:app` as a real
# subprocess pointed at an isolated temp-file database per e2e run, since a subprocess
# can't be handed a `db_path` argument directly the way `create_app()`'s tests can.
app = create_app(os.environ.get("DATABASE_PATH", "servicenow.db"))
```

```python
# app/pagination.py
# Charter-wide foundation file (see plan header's pagination-envelope note under SA-3). Every
# list endpoint in this charter returns the identical {"items", "page", "page_size", "total"}
# envelope; this module is the one shared implementation for endpoints that page an
# already-fetched, small, in-memory row list (e.g. user-directory's `/users`/`/assignment_groups`)
# rather than pushing LIMIT/OFFSET into SQL, which is what GET /incidents (Task 2, this spec) and
# GET /sla (sla-records.plan.md) do instead for their larger row counts — both approaches produce
# the same envelope shape.
from fastapi import Query


class PageParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(50, ge=1, le=200),
    ):
        self.page = page
        self.page_size = page_size


def paginate_rows(rows: list, page: int, page_size: int) -> tuple[list, int]:
    total = len(rows)
    start = (page - 1) * page_size
    return rows[start : start + page_size], total
```

```python
# tests/conftest.py
# Charter-wide foundation file (see plan header). Every sibling itsm-api plan's tests use the
# `client` fixture below unchanged, and use the `conn` fixture for direct fixture-row insertion
# (e.g. seeding a WorkNote, Escalation, TaskSla, SysUser, or AssignmentGroup row without an
# endpoint to create it through). Neither fixture is modified by any sibling plan.
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    application = create_app(str(tmp_path / "test.db"))
    return TestClient(application)


@pytest.fixture
def conn(client):
    return client.app.state.db_conn
```

```
# requirements.txt
fastapi
uvicorn[standard]
pydantic
pytest
httpx
ruff
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_db.py`
Expected: PASS

- [ ] **Commit**

Branch: `feat/itsm-api/incident-lifecycle`

```bash
git add requirements.txt app/ tests/__init__.py tests/conftest.py tests/test_db.py
git commit -m "feat(itsm-api): bootstrap FastAPI app scaffold (charter-wide six-table foundation), Incident table, and Pydantic models"
```

---

### Task 2: Implement `GET /incidents` with filters and pagination [specialist: none]

**Charter capability:** List/get Incident
**Depends on:** Task 1
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/incidents.py` — create the router with the list endpoint (first file
  touch); `app/main.py` — include the router
- Modify: `tests/test_incidents.py` — create (first touch)

**Tests:** `tests/test_incidents.py` (create — BEH-1, BEH-2)

**Context to load:**
- Spec BEH-1, BEH-2; Error Cases table (invalid `opened_after`/`opened_before`)
- Plan header SA-2 (filter validation) and SA-3 (pagination envelope) resolutions

- [ ] **Write failing test**

```python
# tests/test_incidents.py
def _create(conn, number, account_id="ACC-1", state="new", category="network", escalated=0,
            opened_at="2026-01-01T00:00:00Z"):
    conn.execute(
        """
        INSERT INTO incidents
            (number, account_id, category, short_description, description, state,
             priority, opened_at, escalated)
        VALUES (?, ?, ?, 'x', 'x', ?, 1, ?, ?)
        """,
        (number, account_id, category, state, opened_at, escalated),
    )
    conn.commit()


def test_list_incidents_unfiltered_returns_paginated_envelope(client):
    conn = client.app.state.db_conn
    for i in range(3):
        _create(conn, f"TICKET-00000{i}")
    resp = client.get("/incidents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["total"] == 3
    assert len(body["items"]) == 3


def test_list_incidents_filters_by_intersection_of_account_state_and_escalated(client):
    conn = client.app.state.db_conn
    _create(conn, "TICKET-000001", account_id="ACC-1", state="new", escalated=1)
    _create(conn, "TICKET-000002", account_id="ACC-1", state="resolved", escalated=1)
    _create(conn, "TICKET-000003", account_id="ACC-2", state="new", escalated=1)
    resp = client.get("/incidents?account_id=ACC-1&state=new&escalated=true")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["number"] == "TICKET-000001"


def test_list_incidents_opened_after_before_bound_inclusive_exclusive(client):
    conn = client.app.state.db_conn
    _create(conn, "TICKET-000001", opened_at="2026-01-01T00:00:00Z")
    _create(conn, "TICKET-000002", opened_at="2026-01-05T00:00:00Z")
    resp = client.get("/incidents?opened_after=2026-01-01T00:00:00Z&opened_before=2026-01-05T00:00:00Z")
    body = resp.json()
    assert [i["number"] for i in body["items"]] == ["TICKET-000001"]


def test_list_incidents_invalid_state_filter_returns_422(client):
    resp = client.get("/incidents?state=bogus")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "state" in body["message"]
    assert "new" in body["message"]


def test_list_incidents_invalid_escalated_filter_returns_422(client):
    resp = client.get("/incidents?escalated=maybe")
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_list_incidents_unrecognized_category_filter_returns_empty_not_error(client):
    conn = client.app.state.db_conn
    _create(conn, "TICKET-000001", category="network")
    resp = client.get("/incidents?category=nonexistent")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_list_incidents_invalid_opened_after_returns_422(client):
    resp = client.get("/incidents?opened_after=not-a-date")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "opened_after" in body["message"]
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_incidents.py`
Expected: FAIL — `404 Not Found` / `405 Method Not Allowed` (no `/incidents` route registered
yet, `app/routers/incidents.py` doesn't exist).

- [ ] **Implement**

```python
# app/routers/incidents.py
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from app.models import INCIDENT_STATES, IncidentPage, IncidentRead

router = APIRouter()


def _row_to_incident(row) -> IncidentRead:
    return IncidentRead(
        number=row["number"], account_id=row["account_id"], category=row["category"],
        short_description=row["short_description"], description=row["description"],
        state=row["state"], priority=row["priority"], opened_at=row["opened_at"],
        resolved_at=row["resolved_at"], assigned_to=row["assigned_to"],
        assignment_group=row["assignment_group"], escalated=bool(row["escalated"]),
    )


def _parse_iso(value: str, field: str) -> str:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"message": f"{field} is not a valid ISO timestamp", "code": "VALIDATION_ERROR"},
        )
    return value


def _parse_bool(value: str, field: str) -> bool:
    if value.lower() in ("true", "1"):
        return True
    if value.lower() in ("false", "0"):
        return False
    raise HTTPException(
        status_code=422,
        detail={"message": f"{field} must be one of: true, false", "code": "VALIDATION_ERROR"},
    )


@router.get("/incidents", response_model=IncidentPage)
def list_incidents(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    account_id: str | None = None,
    state: str | None = None,
    category: str | None = None,
    opened_after: str | None = None,
    opened_before: str | None = None,
    escalated: str | None = None,
):
    if state is not None and state not in INCIDENT_STATES:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"state must be one of: {', '.join(INCIDENT_STATES)}",
                "code": "VALIDATION_ERROR",
            },
        )
    escalated_bool = _parse_bool(escalated, "escalated") if escalated is not None else None
    if opened_after is not None:
        _parse_iso(opened_after, "opened_after")
    if opened_before is not None:
        _parse_iso(opened_before, "opened_before")

    conn = request.app.state.db_conn
    query = "SELECT * FROM incidents WHERE 1=1"
    params: list = []
    if account_id is not None:
        query += " AND account_id = ?"
        params.append(account_id)
    if state is not None:
        query += " AND state = ?"
        params.append(state)
    if category is not None:
        query += " AND category = ?"
        params.append(category)
    if opened_after is not None:
        query += " AND opened_at >= ?"
        params.append(opened_after)
    if opened_before is not None:
        query += " AND opened_at < ?"
        params.append(opened_before)
    if escalated_bool is not None:
        query += " AND escalated = ?"
        params.append(1 if escalated_bool else 0)

    total = conn.execute(
        query.replace("SELECT *", "SELECT COUNT(*) AS c", 1), params
    ).fetchone()["c"]
    query += " ORDER BY number ASC LIMIT ? OFFSET ?"
    params.extend([page_size, (page - 1) * page_size])
    rows = conn.execute(query, params).fetchall()

    return IncidentPage(
        items=[_row_to_incident(r) for r in rows], page=page, page_size=page_size, total=total
    )
```

```python
# app/main.py (modify)
from app.routers.incidents import router as incidents_router

# inside create_app, before `return app`:
app.include_router(incidents_router)
```

Note on `opened_after`/`opened_before` (BEH-2): "inclusive/exclusive per ISO-timestamp comparison"
is implemented as `opened_after` → `>=` (inclusive lower bound) and `opened_before` → `<`
(exclusive upper bound) — string comparison is correct here because all `opened_at` values are
ISO-8601 UTC timestamps, which sort lexicographically in chronological order.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_incidents.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/ app/main.py tests/test_incidents.py
git commit -m "feat(itsm-api): implement GET /incidents with filters, pagination envelope, and filter validation"
```

---

### Task 3: Implement `GET /incidents/{number}` [specialist: none]

**Charter capability:** List/get Incident
**Depends on:** Task 2
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/incidents.py` — add get-by-number endpoint
- Modify: `tests/test_incidents.py` — extend

**Tests:** `tests/test_incidents.py` (extend — BEH-3, BEH-4)

**Context to load:**
- Spec BEH-3, BEH-4; Error Cases table (`INCIDENT_NOT_FOUND`)

- [ ] **Write failing test**

```python
# tests/test_incidents.py (append)
def test_get_incident_by_number_returns_200(client):
    conn = client.app.state.db_conn
    _create(conn, "TICKET-000042")
    resp = client.get("/incidents/TICKET-000042")
    assert resp.status_code == 200
    assert resp.json()["number"] == "TICKET-000042"


def test_get_incident_unknown_number_returns_404(client):
    resp = client.get("/incidents/TICKET-999999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "INCIDENT_NOT_FOUND"
    assert "TICKET-999999" in body["message"]
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_incidents.py::test_get_incident_by_number_returns_200 tests/test_incidents.py::test_get_incident_unknown_number_returns_404`
Expected: FAIL — `404 Not Found` from FastAPI's default (route doesn't exist), so even the "not
found" test fails: it gets a generic Starlette 404 body, not the `INCIDENT_NOT_FOUND` envelope.

- [ ] **Implement**

```python
# app/routers/incidents.py (append)
@router.get("/incidents/{number}", response_model=IncidentRead)
def get_incident(number: str, request: Request):
    conn = request.app.state.db_conn
    row = conn.execute("SELECT * FROM incidents WHERE number = ?", (number,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Incident {number} not found", "code": "INCIDENT_NOT_FOUND"},
        )
    return _row_to_incident(row)
```

Route ordering note: this route must be declared **after** `GET /incidents` (Task 2) in the
router — with FastAPI/Starlette that ordering doesn't actually matter here since `/incidents` and
`/incidents/{number}` aren't ambiguous (no path collision), but it's kept in declaration order to
match this plan's task order for readability.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_incidents.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/incidents.py tests/test_incidents.py
git commit -m "feat(itsm-api): implement GET /incidents/{number} with 404 handling"
```

---

### Task 4: Implement `POST /incidents` [specialist: none]

**Charter capability:** Create/update Incident
**Depends on:** Task 3
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/incidents.py` — add create endpoint
- Modify: `tests/test_incidents.py` — extend

**Tests:** `tests/test_incidents.py` (extend — BEH-5, BEH-6, BEH-7 create-half, plus one
`MALFORMED_JSON` check for the shared handler)

**Context to load:**
- Spec BEH-5, BEH-6, BEH-7; Error Cases table (`VALIDATION_ERROR`, `MALFORMED_JSON`)
- Plan header SA-1 resolution: `opened_at` server-assigned, `assignment_group` defaults null

- [ ] **Write failing test**

```python
# tests/test_incidents.py (append)
_REQUIRED = {
    "account_id": "ACC-1", "category": "network", "short_description": "Router down",
    "description": "Router down since 9am", "state": "new", "priority": 2,
}


def test_create_incident_returns_201_with_server_assigned_number_and_defaults(client):
    resp = client.post("/incidents", json=_REQUIRED)
    assert resp.status_code == 201
    body = resp.json()
    assert body["number"] == "TICKET-000001"
    assert body["escalated"] is False
    assert body["resolved_at"] is None
    assert body["assigned_to"] is None
    assert body["assignment_group"] is None
    assert body["opened_at"] is not None


def test_create_second_incident_number_never_collides(client):
    client.post("/incidents", json=_REQUIRED)
    resp = client.post("/incidents", json=_REQUIRED)
    assert resp.json()["number"] == "TICKET-000002"


def test_create_incident_retrievable_immediately_via_get_list_and_get_by_number(client):
    created = client.post("/incidents", json=_REQUIRED).json()
    assert client.get(f"/incidents/{created['number']}").status_code == 200
    listed = client.get(f"/incidents?account_id={_REQUIRED['account_id']}").json()
    assert created["number"] in [i["number"] for i in listed["items"]]


def test_create_incident_missing_required_field_returns_422_and_creates_nothing(client):
    payload = dict(_REQUIRED)
    del payload["short_description"]
    resp = client.post("/incidents", json=payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "short_description" in body["message"]
    assert client.get("/incidents").json()["total"] == 0


def test_create_incident_invalid_state_returns_422_naming_allowed_values(client):
    payload = dict(_REQUIRED, state="bogus")
    resp = client.post("/incidents", json=payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "state" in body["message"]


def test_create_incident_invalid_priority_returns_422(client):
    payload = dict(_REQUIRED, priority=9)
    resp = client.post("/incidents", json=payload)
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_create_incident_malformed_json_returns_400(client):
    resp = client.post(
        "/incidents", content=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "MALFORMED_JSON"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_incidents.py::test_create_incident_returns_201_with_server_assigned_number_and_defaults`
Expected: FAIL — `405 Method Not Allowed` (no `POST /incidents` route yet).

- [ ] **Implement**

```python
# app/routers/incidents.py (append)
from datetime import datetime, timezone

from app.db import next_incident_number
from app.models import IncidentCreate


@router.post("/incidents", response_model=IncidentRead, status_code=201)
def create_incident(payload: IncidentCreate, request: Request):
    conn = request.app.state.db_conn
    number = next_incident_number(conn)
    opened_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO incidents
            (number, account_id, category, short_description, description, state,
             priority, opened_at, resolved_at, assigned_to, assignment_group, escalated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            number, payload.account_id, payload.category, payload.short_description,
            payload.description, payload.state, payload.priority, opened_at,
            payload.resolved_at, payload.assigned_to, payload.assignment_group,
            1 if payload.escalated else 0,
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM incidents WHERE number = ?", (number,)).fetchone()
    return _row_to_incident(row)
```

`opened_at` is computed server-side in the handler and is not a field on `IncidentCreate` at all
(Task 1) — there is no path for a client to set it, resolving SA-1 structurally, the same pattern
Task 1 already used for `number`/`assignment_group` immutability-by-omission.
`state`/`priority` enum validation (BEH-7, create half) is enforced entirely by `IncidentCreate`'s
`Literal[...]` types (Task 1); an out-of-set value raises `RequestValidationError`, caught by
`app/errors.py`'s `literal_error` branch (Task 1) before this handler body ever runs — no row is
inserted, satisfying BEH-6/BEH-7's "creates no Incident" / "persists no change".

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_incidents.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/incidents.py tests/test_incidents.py
git commit -m "feat(itsm-api): implement POST /incidents with server-assigned number and opened_at"
```

---

### Task 5: Implement `PATCH /incidents/{number}` [specialist: none]

**Charter capability:** Create/update Incident
**Depends on:** Task 4
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/incidents.py` — add partial-update endpoint
- Modify: `tests/test_incidents.py` — extend

**Tests:** `tests/test_incidents.py` (extend — BEH-7 patch-half, BEH-8, BEH-9)

**Context to load:**
- Spec BEH-7, BEH-8, BEH-9; Preconditions (no permission/business-rule guard — constitution
  Non-Negotiable Principle 5); Postconditions ("`number` never changes once assigned")
- `IncidentPatch` (Task 1) has no `number`/`account_id`/`opened_at` field — structural
  immutability, same pattern as `mock-jira`'s `IssuePatch`

- [ ] **Write failing test**

```python
# tests/test_incidents.py (append)
def test_patch_incident_updates_given_fields_and_returns_200(client):
    created = client.post("/incidents", json=_REQUIRED).json()
    resp = client.patch(
        f"/incidents/{created['number']}",
        json={"state": "resolved", "priority": 1, "assigned_to": "dana", "assignment_group": "Support Tier 1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "resolved"
    assert body["priority"] == 1
    assert body["assigned_to"] == "dana"
    assert body["assignment_group"] == "Support Tier 1"


def test_patch_incident_ignores_number_and_account_id_and_opened_at_in_body(client):
    created = client.post("/incidents", json=_REQUIRED).json()
    resp = client.patch(
        f"/incidents/{created['number']}",
        json={"number": "TICKET-999999", "account_id": "ACC-OTHER",
              "opened_at": "2000-01-01T00:00:00Z", "priority": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["number"] == created["number"]
    assert body["account_id"] == created["account_id"]
    assert body["opened_at"] == created["opened_at"]
    assert body["priority"] == 3


def test_patch_incident_allows_resolving_with_no_business_rule_guard(client):
    # Preconditions: any actor may resolve any Incident regardless of open SLA breach or
    # unanswered customer — this HTTP layer adds no such guard (constitution Principle 5).
    created = client.post("/incidents", json=dict(_REQUIRED, state="new")).json()
    resp = client.patch(f"/incidents/{created['number']}", json={"state": "closed"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "closed"


def test_patch_incident_invalid_state_returns_422_and_persists_no_change(client):
    created = client.post("/incidents", json=_REQUIRED).json()
    resp = client.patch(f"/incidents/{created['number']}", json={"state": "bogus"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "state" in body["message"]
    unchanged = client.get(f"/incidents/{created['number']}").json()
    assert unchanged["state"] == _REQUIRED["state"]


def test_patch_incident_invalid_priority_returns_422(client):
    created = client.post("/incidents", json=_REQUIRED).json()
    resp = client.patch(f"/incidents/{created['number']}", json={"priority": 9})
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_patch_incident_unknown_number_returns_404(client):
    resp = client.patch("/incidents/TICKET-999999", json={"priority": 2})
    assert resp.status_code == 404
    assert resp.json()["code"] == "INCIDENT_NOT_FOUND"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_incidents.py::test_patch_incident_updates_given_fields_and_returns_200`
Expected: FAIL — `405 Method Not Allowed` (no `PATCH /incidents/{number}` route yet).

- [ ] **Implement**

```python
# app/routers/incidents.py (append)
from app.models import IncidentPatch

_PATCHABLE_FIELDS = ("state", "priority", "assigned_to", "assignment_group")


@router.patch("/incidents/{number}", response_model=IncidentRead)
def patch_incident(number: str, payload: IncidentPatch, request: Request):
    conn = request.app.state.db_conn
    row = conn.execute("SELECT * FROM incidents WHERE number = ?", (number,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"message": f"Incident {number} not found", "code": "INCIDENT_NOT_FOUND"},
        )

    updates = payload.model_dump(exclude_unset=True)
    set_clauses = [f"{field} = ?" for field in _PATCHABLE_FIELDS if field in updates]
    values = [updates[field] for field in _PATCHABLE_FIELDS if field in updates]
    if set_clauses:
        conn.execute(
            f"UPDATE incidents SET {', '.join(set_clauses)} WHERE number = ?",
            (*values, number),
        )
        conn.commit()

    row = conn.execute("SELECT * FROM incidents WHERE number = ?", (number,)).fetchone()
    return _row_to_incident(row)
```

Two independent structural layers enforce BEH-8's immutability clause, mirroring `mock-jira`'s
`PATCH /issues/{id}` (Task 1's plan-header pattern reference): (1) `IncidentPatch` (Task 1) has no
`number`/`account_id`/`opened_at` field, so `payload.model_dump(exclude_unset=True)` can never
contain those keys even if the raw request JSON does; (2) `_PATCHABLE_FIELDS` is a fixed allow-list
the `UPDATE`'s `SET` clause is built from regardless. Neither this handler nor any code it calls
checks whether the `state` transition is sensible, whether `assigned_to` is a known user, or
whether an SLA breach is open — per BEH-8 and constitution Principle 5, that guard is intentionally
absent at every layer, not merely unenforced here. `state`/`priority` enum validation (BEH-7, patch
half) reuses the identical `Literal[...]`-typed fields and `literal_error` handler branch as
`POST` (Task 1/4), so the two endpoints can never drift on what counts as a valid value.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_incidents.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/incidents.py tests/test_incidents.py
git commit -m "feat(itsm-api): implement PATCH /incidents/{number} with structural immutability, no business-rule guard"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are
recorded in the validation report (`.validate.md`), not in this plan. `governance/gates.yaml`
defines the authoritative commands (mirrored in the constitution's Quality Gates section):

- **Test Suite** (`test`, deterministic, required, severity error): `python3 -m pytest -q`
- **Linter** (`lint`, deterministic, required, severity error): `ruff check .`
- **Integration Tests** (`integration-test`, deterministic, required): command is unwired
  (`command: ""` in `gates.yaml`). **Skipped** for this plan — nothing here requires more than the
  unit-level `TestClient` coverage above.
- All acceptance criteria from `incident-lifecycle.spec.md` satisfied (BEH-1 through BEH-9).
- No constitutional violations: no permission/business-rule guard added to `PATCH
  /incidents/{number}` (Principle 5); no cross-repo dependency introduced (Principle 1); no
  breaking change to an already-shipped contract (there is none yet).
