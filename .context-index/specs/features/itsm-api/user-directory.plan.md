<!-- partial_schema: plan@1 -->

# Implementation Plan: User and assignment group directory

> **Methodology:** adev
> **Charter:** .context-index/specs/features/itsm-api/charter.md
> **Spec:** .context-index/specs/features/itsm-api/user-directory.spec.md
> **Review:** PASS (2026-09-07, revision 2 — re-review after a revision-1 BLOCK; see
> `user-directory.review.md`)
> **Platform:** FastAPI over SQLite, Python 3.11, Pydantic, pytest/httpx — per this repo's
> constitution "Patterns to Follow" ("Follow `mock-jira`'s shape"); `platform-context.yaml`'s
> `framework: none` predates this plan and is not amended here (out of scope for `/adev:plan`).

**Goal:** Serve a read-only, paginated `GET /users` and `GET /assignment_groups` directory over
SysUser/AssignmentGroup SQLite tables, matching the spec's field-level schema exactly.

**Architecture:** Per a cross-plan consistency pass (2026-09-07), `incident-lifecycle.plan.md`'s
Task 1 is this charter's designated canonical foundation owner: it creates `app/db.py` (with
`create_schema()` already covering **all six** charter tables, including `assignment_group` and
`sys_user`), `app/models.py`, `app/errors.py`, `app/main.py`, `app/pagination.py`,
`requirements.txt`, and `tests/conftest.py` (the `client`/`conn` fixtures). This plan's Task 1
**depends on** that foundation and **extends** `app/models.py` with this spec's own
`AssignmentGroupRead`/`SysUserRead`/`PaginatedAssignmentGroups`/`PaginatedUsers` models — it does
not recreate the `assignment_group`/`sys_user` tables in `create_schema()` (already defined there)
or any of the other shared files, including `app/pagination.py`'s `PageParams`/`paginate_rows()`
helper, which this plan's two endpoints now consume directly rather than reinventing. No seed
command exists yet (`fixture-seeding` is a separate, not-yet-planned spec), so every test in this
plan inserts SysUser/AssignmentGroup rows directly via the SQLite connection rather than relying
on seeded data — consistent with `user-directory.spec.md`'s Actionable Task Map, which scopes only
schema + the two `GET` endpoints, not seeding.

**Constitution Validation:** No task adds a workspace-repo dependency, touches auth, or writes to
Incident/WorkNote/Escalation/TaskSla rows (Postconditions). No create/update/delete endpoint is
added for either entity, matching the spec's explicit non-goal and the charter's Deferred
Capabilities row ("Create/delete SysUser or AssignmentGroup via API"). No task is
`[REQUIRES HUMAN APPROVAL]`.

**Review notes carried forward:** revision 2's fixes (explicit field-level schema; the
authoring-time name-invention reconciliation note) are spec-level and already resolved before
this plan was written — no outstanding review note applies to planning itself.

---

## File Structure

**Create:**
- `app/routers/__init__.py` — package marker
- `app/routers/directory.py` — `GET /users`, `GET /assignment_groups`
- `pytest.ini` — `[pytest]` / `testpaths = tests` (not part of the shared foundation this plan
  depends on — `api-e2e.plan.md`'s Task 11 creates the same file, with the same content, for its
  own `tests_e2e/`-isolation reason; whichever plan lands first creates it, the other finds it
  already correct and needs no change)
- `tests/test_directory.py` — BEH-1 through BEH-4 and the pagination-validation error case

**Modify (extending files `incident-lifecycle.plan.md`'s Task 1 already created — cross-plan
dependency, not created fresh by this plan):**
- `app/models.py` — add `AssignmentGroupRead`, `SysUserRead`, `PaginatedAssignmentGroups`,
  `PaginatedUsers`
- `app/main.py` — include the `directory` router
- `tests/conftest.py` — nothing to add beyond the existing `client`/`conn` fixtures (this plan's
  tests use `conn` directly for SysUser/AssignmentGroup row insertion)

**Reference (read, do not modify — created by `incident-lifecycle.plan.md`'s Task 1, the charter's
canonical foundation; cross-plan dependency, not created by this plan):**
- `app/db.py` — `get_connection(db_path)`, `create_schema(conn)` (already creates
  `assignment_group` and `sys_user`, among all six charter tables, per the spec's field-level
  schema)
- `app/errors.py` — `validation_exception_handler`, `http_exception_handler`, already generalized
  to name invalid query parameters (`page`/`page_size`) as well as body fields — no change needed
  for this plan
- `app/pagination.py` — `PageParams` (FastAPI `Depends`-able page/page_size query params) and
  `paginate_rows(rows, page, page_size)` helper — this plan's two endpoints consume it directly
- `requirements.txt` — `fastapi`, `uvicorn[standard]`, `pydantic`, `pytest`, `httpx`, `ruff`
- `tests/conftest.py`'s `client`/`conn` fixtures (isolated temp-SQLite `TestClient` + connection
  per test, full six-table schema pre-applied)
- `.context-index/specs/features/itsm-api/charter.md` — Domain Model (SysUser/AssignmentGroup),
  Capability Map row "List users and assignment groups", Quality Attributes (pagination
  requirement), Interface Contracts
- `.context-index/specs/features/itsm-api/user-directory.spec.md` — field-level schema
  (Preconditions), BEH-1..4, Error Cases
- `/Users/dpavancini/Development/adev-course/mock-jira/app/db.py`,
  `app/routers/projects.py`, `app/errors.py`, `app/main.py`, `tests/conftest.py` — the FastAPI/
  SQLite/pytest pattern this plan mirrors (different repo; read-only reference, never imported)

---

## Context Packets

### Task 1 Context
- Spec: `user-directory.spec.md` Preconditions ("Field-level schema" bullet — `SysUser.name` PK,
  `role`, `assignment_group` nullable FK-by-name; `AssignmentGroup.name` PK); BEH-2 ("exactly
  three AssignmentGroup records... no more, no fewer"); Error Cases table (`VALIDATION_ERROR` for
  invalid pagination parameter)
- Charter: Domain Model → SysUser/AssignmentGroup rows; Quality Attributes → pagination
  requirement
- **Cross-plan dependency:** `incident-lifecycle.plan.md` Task 1 — `app/db.py`'s
  `create_schema()` already defines the `assignment_group`/`sys_user` tables; `app/models.py`,
  `app/errors.py`, `app/main.py`, `app/pagination.py`, `requirements.txt`, `tests/conftest.py`
  (`client`/`conn` fixtures) already exist. Full read of `app/db.py`, `app/models.py`,
  `app/errors.py`, `app/main.py`, `app/pagination.py`, `tests/conftest.py` before starting —
  extending these files, not recreating them.
- Reference: `mock-jira/app/routers/projects.py::list_projects` (list-endpoint pattern),
  `mock-jira/app/errors.py` (validation error envelope shape), `mock-jira/app/models.py`
  (Pydantic response-model shape)

### Task 2 Context
- Spec: BEH-1 (full directory, paginated), BEH-3 (every SysUser's group membership names one of
  the three AssignmentGroups)
- Reference: Task 1's `app/routers/directory.py` (extends the same file)

### Task 3 Context
- Spec: BEH-4 (paginated page shape on both endpoints even when everything fits one page); Error
  Cases table (non-integer `page`/`page_size` → `422 VALIDATION_ERROR`)
- Reference: `app/pagination.py` (`incident-lifecycle.plan.md` Task 1, cross-plan), both router
  functions (Tasks 1-2)

---

## Parallelization

- Group A (sequential): Task 1 → Task 2 → Task 3

All three tasks touch the same small set of files (`app/models.py`, `app/routers/directory.py`,
`tests/test_directory.py`) being built up incrementally within this plan — no independent group
exists to parallelize against.

**Depends on (cross-plan):** Task 1 depends on `incident-lifecycle.plan.md` Task 1 (the charter's
canonical foundation — `app/db.py`'s `create_schema()` already defines the `assignment_group`/
`sys_user` tables; `app/models.py`, `app/errors.py`, `app/main.py`, `app/pagination.py`,
`requirements.txt`, `tests/conftest.py` already exist). This plan cannot begin until that task
has landed.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Implement `GET /assignment_groups` (BEH-2) | small | unit | *(cross-plan)* incident-lifecycle Task 1 | 2 create, 2 modify |
| 2 | Implement `GET /users` (BEH-1, BEH-3) | small | unit | Task 1 | 0 create, 1 modify |
| 3 | Pagination shape + invalid-parameter validation (BEH-4, error case) | small | unit | Task 1, Task 2 | 0 create, 1 modify |

All tasks resolve to the `unit` strategy (fallback — no `test_strategy` in spec frontmatter, no
matching `test_strategies` entries in `manifest.yaml`).

**Granularity:** `per-behavior` (source: manifest `test_policy.granularity`). `tests/test_directory.py`
is created once (Task 1, covering BEH-2 and the SysUser/AssignmentGroup model shapes) and extended
by every subsequent task for its own behavior(s). No separate schema task exists in this plan —
`incident-lifecycle.plan.md` Task 1's `create_schema()` already defines and tests the
`assignment_group`/`sys_user` tables as part of the charter-wide foundation.

---

## Task Structure

### Task 1: Implement `GET /assignment_groups` (BEH-2) [specialist: none]

**Charter capability:** List users and assignment groups
**Depends on:** *(cross-plan)* `incident-lifecycle.plan.md` Task 1 — the charter's canonical
foundation. `app/db.py`'s `create_schema()` already defines the `assignment_group`/`sys_user`
tables; `app/models.py`, `app/errors.py`, `app/main.py`, `app/pagination.py`, `requirements.txt`,
and `tests/conftest.py` (`client`/`conn` fixtures) already exist and are extended here, not
recreated.
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `app/routers/__init__.py`, `app/routers/directory.py`, `pytest.ini`
- Modify: `app/models.py` — add `AssignmentGroupRead`, `SysUserRead`,
  `PaginatedAssignmentGroups`, `PaginatedUsers`
- Modify: `app/main.py` — include the `directory` router
- Test: `tests/test_directory.py` (create)

**Tests:** `tests/test_directory.py` (create — covers BEH-2 and the model shapes)

**Context to load:**
- Spec: `user-directory.spec.md` Preconditions ("Field-level schema" bullet — `SysUser.name` PK,
  `role`, `assignment_group` nullable FK-by-name; `AssignmentGroup.name` PK); BEH-2
- Charter: Domain Model → SysUser/AssignmentGroup rows; Quality Attributes → pagination
  requirement
- `incident-lifecycle.plan.md` Task 1's `app/db.py`, `app/models.py`, `app/errors.py`,
  `app/main.py`, `app/pagination.py`, `tests/conftest.py` (full read — extending, not replacing)
- Reference: `mock-jira/app/routers/projects.py::list_projects` (list-endpoint pattern)

- [ ] **Write failing test**

```python
# app/models.py (append — extends incident-lifecycle Task 1's file)
class AssignmentGroupRead(BaseModel):
    name: str


class SysUserRead(BaseModel):
    name: str
    role: str
    assignment_group: str | None = None


class PaginatedAssignmentGroups(BaseModel):
    items: list[AssignmentGroupRead]
    page: int
    page_size: int
    total: int


class PaginatedUsers(BaseModel):
    items: list[SysUserRead]
    page: int
    page_size: int
    total: int
```

```python
# tests/test_directory.py
def test_create_schema_creates_sys_user_and_assignment_group_tables(conn):
    conn.execute(
        "INSERT INTO assignment_group (name) VALUES (?)", ("Support Tier 1",)
    )
    conn.execute(
        "INSERT INTO sys_user (name, role, assignment_group) VALUES (?, ?, ?)",
        ("Rui Bastos", "Support Manager", None),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM sys_user WHERE name = ?", ("Rui Bastos",)).fetchone()
    assert row["role"] == "Support Manager"
    assert row["assignment_group"] is None


def test_paginate_rows_slices_and_reports_total():
    from app.pagination import paginate_rows

    rows = list(range(1, 11))
    items, total = paginate_rows(rows, page=2, page_size=4)
    assert items == [5, 6, 7, 8]
    assert total == 10


def test_list_assignment_groups_returns_exactly_the_three_named_groups(client, conn):
    for name in ("Support Tier 1", "Support Tier 2", "Solution Consultants"):
        conn.execute("INSERT INTO assignment_group (name) VALUES (?)", (name,))
    conn.commit()

    resp = client.get("/assignment_groups")

    assert resp.status_code == 200
    body = resp.json()
    names = {g["name"] for g in body["items"]}
    assert names == {"Support Tier 1", "Support Tier 2", "Solution Consultants"}
    assert body["total"] == 3
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_directory.py`
Expected: FAIL — `404 Not Found` (no `/assignment_groups` route registered yet;
`app/routers/directory.py` doesn't exist). `app/pagination.py::paginate_rows` already exists
(`incident-lifecycle.plan.md` Task 1), so `test_paginate_rows_slices_and_reports_total` passes
immediately — that is expected, not a failure to fix.

- [ ] **Implement**

```python
# app/routers/directory.py
from fastapi import APIRouter, Depends, Request

from app.models import PaginatedAssignmentGroups, AssignmentGroupRead
from app.pagination import PageParams, paginate_rows

router = APIRouter()


@router.get("/assignment_groups", response_model=PaginatedAssignmentGroups)
def list_assignment_groups(request: Request, page_params: PageParams = Depends()):
    conn = request.app.state.db_conn
    rows = conn.execute("SELECT * FROM assignment_group ORDER BY name ASC").fetchall()
    items, total = paginate_rows(rows, page_params.page, page_params.page_size)
    return PaginatedAssignmentGroups(
        items=[AssignmentGroupRead(name=r["name"]) for r in items],
        page=page_params.page,
        page_size=page_params.page_size,
        total=total,
    )
```

```python
# app/main.py (modify)
from app.routers.directory import router as directory_router

# inside create_app, before `return app`:
app.include_router(directory_router)
```

```ini
# pytest.ini
[pytest]
testpaths = tests
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_directory.py`
Expected: PASS

- [ ] **Commit**

Branch (if not already created): `feat/itsm-api/user-directory`

```bash
git add app/models.py app/main.py app/routers/__init__.py app/routers/directory.py \
  pytest.ini tests/test_directory.py
git commit -m "feat(itsm-api): implement GET /assignment_groups with SysUser/AssignmentGroup models"
```

---

### Task 2: Implement `GET /users` (BEH-1, BEH-3) [specialist: none]

**Depends on:** Task 1
**Charter capability:** List users and assignment groups
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/routers/directory.py`

**Tests:** `tests/test_directory.py` (extend)

- [ ] **Write failing test**

```python
def _seed_directory(conn):
    for name in ("Support Tier 1", "Support Tier 2", "Solution Consultants"):
        conn.execute("INSERT INTO assignment_group (name) VALUES (?)", (name,))
    conn.execute(
        "INSERT INTO sys_user (name, role, assignment_group) VALUES (?, ?, ?)",
        ("Rui Bastos", "Support Manager", None),
    )
    conn.execute(
        "INSERT INTO sys_user (name, role, assignment_group) VALUES (?, ?, ?)",
        ("Priya Nair", "Solution Consultant", "Solution Consultants"),
    )
    conn.execute(
        "INSERT INTO sys_user (name, role, assignment_group) VALUES (?, ?, ?)",
        ("Joao Pinto", "Support Engineer", "Support Tier 1"),
    )
    conn.commit()


def test_list_users_returns_full_seeded_directory(client, conn):
    _seed_directory(conn)

    resp = client.get("/users")

    assert resp.status_code == 200
    body = resp.json()
    names = {u["name"] for u in body["items"]}
    assert names == {"Rui Bastos", "Priya Nair", "Joao Pinto"}
    assert body["total"] == 3


def test_every_user_group_membership_names_a_known_assignment_group(client, conn):
    _seed_directory(conn)
    valid_groups = {"Support Tier 1", "Support Tier 2", "Solution Consultants"}

    resp = client.get("/users")

    for user in resp.json()["items"]:
        if user["assignment_group"] is not None:
            assert user["assignment_group"] in valid_groups
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_directory.py`
Expected: FAIL — `404 Not Found` (no `/users` route registered yet)

- [ ] **Implement**

```python
# app/routers/directory.py (append)
from app.models import PaginatedUsers, SysUserRead


@router.get("/users", response_model=PaginatedUsers)
def list_users(request: Request, page_params: PageParams = Depends()):
    conn = request.app.state.db_conn
    rows = conn.execute("SELECT * FROM sys_user ORDER BY name ASC").fetchall()
    items, total = paginate_rows(rows, page_params.page, page_params.page_size)
    return PaginatedUsers(
        items=[
            SysUserRead(name=r["name"], role=r["role"], assignment_group=r["assignment_group"])
            for r in items
        ],
        page=page_params.page,
        page_size=page_params.page_size,
        total=total,
    )
```

BEH-3 is a data-integrity property of the seed/fixture data (every `sys_user.assignment_group`
value is either `NULL` or a name present in `assignment_group`), not something this endpoint
enforces at read time — the endpoint returns whatever is stored. The test above is the guard;
enforcing the FK at the SQLite layer (`REFERENCES assignment_group(name)`, added in
`incident-lifecycle.plan.md`'s cross-plan Task 1) is the mechanism that keeps it true for any row
inserted after schema creation.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_directory.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/routers/directory.py tests/test_directory.py
git commit -m "feat(itsm-api): implement GET /users"
```

### Task 3: Pagination page shape and invalid-parameter validation (BEH-4, error case) [specialist: none]

**Depends on:** Task 1, Task 2
**Charter capability:** List users and assignment groups
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Test: `tests/test_directory.py` (extend) — no production code change expected; see below

**Tests:** `tests/test_directory.py` (extend)

**Context to load:**
- Spec BEH-4 (paginated page shape on both endpoints even when everything fits one page); Error
  Cases table (non-integer `page`/`page_size` → `422 VALIDATION_ERROR`)
- Reference: `app/pagination.py` and `app/errors.py` (`incident-lifecycle.plan.md` Task 1,
  cross-plan), both router functions (Tasks 1-2)

- [ ] **Write failing test**

```python
def test_users_page_shape_returns_all_rows_in_one_page_by_default(client, conn):
    _seed_directory(conn)

    resp = client.get("/users")

    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] >= body["total"]
    assert len(body["items"]) == body["total"]


def test_assignment_groups_page_shape_returns_all_rows_in_one_page_by_default(client, conn):
    for name in ("Support Tier 1", "Support Tier 2", "Solution Consultants"):
        conn.execute("INSERT INTO assignment_group (name) VALUES (?)", (name,))
    conn.commit()

    resp = client.get("/assignment_groups")

    body = resp.json()
    assert body["page"] == 1
    assert len(body["items"]) == body["total"] == 3


def test_get_users_with_non_integer_page_returns_422_validation_error(client):
    resp = client.get("/users", params={"page": "not-a-number"})

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "page" in body["message"]


def test_get_assignment_groups_with_non_integer_page_size_returns_422_validation_error(client):
    resp = client.get("/assignment_groups", params={"page_size": "lots"})

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "page_size" in body["message"]
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_directory.py`
Expected: all four assertions PASS immediately, no code change needed. The page-shape assertions
already hold (Tasks 1-2's default `page_size=50` covers the small directory). The two
validation assertions also already hold: `incident-lifecycle.plan.md`'s (cross-plan) Task 1
`validation_exception_handler` reads `errors[0]["loc"][-1]` for the field name regardless of
whether the error came from a body field or a query parameter, and its fallback branch
(`"{field} is required"`) already includes the field name and the `VALIDATION_ERROR` code for
any error type it doesn't special-case, including a non-integer `page`/`page_size` (Pydantic's
`int_parsing` type). This step exists to prove BEH-4 and the error case are genuine, tested
consequences of the shared foundation and Tasks 1-2's implementation, per this plan's TDD
discipline, not to fix a gap.

- [ ] **Implement**

No implementation change. If the "Verify test fails" step above surfaces an unexpected failure,
fix it in `app/pagination.py`/`app/errors.py` here and re-run; this task's own code-change budget
covers exactly and only that contingency.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_directory.py`
Expected: PASS — full file, all BEH-1 through BEH-4 plus the error case green.

- [ ] **Commit**

```bash
git add tests/test_directory.py
git commit -m "test(itsm-api): verify pagination page shape and invalid-parameter validation for directory endpoints"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are
recorded in the validation report (`.validate.md`), not in this plan.

- Tests pass: `python3 -m pytest -q` (per `.context-index/governance/gates.yaml`'s `test` gate)
- Lint passes: `ruff check .` (per `.context-index/governance/gates.yaml`'s `lint` gate)
- `integration-test` gate in `governance/gates.yaml` is unwired (`command: ""`) — skipped, not
  applicable to this plan
- All acceptance criteria from `user-directory.spec.md` satisfied:
  - [ ] `GET /users` returns the full seeded directory, paginated (BEH-1)
  - [ ] `GET /assignment_groups` returns exactly the three named groups (BEH-2)
  - [ ] Every SysUser's group membership names one of the three AssignmentGroups (BEH-3)
  - [ ] Both endpoints return a paginated page shape (BEH-4)
  - [ ] No create/update/delete endpoint exists for either entity this milestone
  - [ ] All quality gates pass (tests, lint)
  - [ ] No constitutional violations introduced
