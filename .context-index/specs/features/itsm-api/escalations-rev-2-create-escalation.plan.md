<!-- partial_schema: plan@1 -->

# Implementation Plan: Escalation Create (POST /escalations)

> **Methodology:** adev
> **Charter:** .context-index/specs/features/itsm-api/charter.md
> **Spec:** .context-index/specs/features/itsm-api/escalations-rev-2-create-escalation.spec.md
> **Review:** PASS_WITH_NOTES (2026-09-09)
> **Platform:** no framework declared in platform-context.yaml (existing code uses FastAPI-style routers), Python 3.11, SQLite, no ORM

**Goal:** Add `POST /escalations`, a server-assigned-identifier create endpoint for the Escalation entity, mirroring the existing `POST /incidents` pattern.

**Architecture:** Two files change plus their test suites. `app/db.py` gains `next_escalation_number`, a next-max-suffix allocator identical in shape to the existing `next_incident_number`. `app/models.py` gains `EscalationCreate`, and `app/routers/escalations.py` gains the route handler — both modeled directly on `IncidentCreate`/`create_incident`. `app/errors.py` needs no change: its `RequestValidationError` handler is already generalized across every Literal/bool-typed field and every entity's `MALFORMED_JSON`/`VALIDATION_ERROR` shape (see its own header comment), so the new endpoint's 422/400 cases are covered for free.

---

## File Structure

**Modify:**
- `app/db.py` — add `next_escalation_number(conn)` after `next_incident_number`
- `app/models.py` — add `EscalationCreate` model after `EscalationRead`
- `app/routers/escalations.py` — add `create_escalation` route handler
- `tests/test_db.py` — add `next_escalation_number` unit tests, mirroring the existing `next_incident_number` tests
- `tests/test_escalations.py` — add `POST /escalations` behavior tests (BEH-9 through BEH-13)

**Reference (read, do not modify):**
- `app/routers/incidents.py:123-145` — `create_incident`, the pattern this endpoint mirrors (server-assigned `number`/`opened_at`, 201 response)
- `app/db.py:165-174` — `next_incident_number`, the allocator pattern to mirror for `ESCALATION-NNNN`
- `app/models.py:13-23` — `IncidentCreate`, the Pydantic model pattern to mirror
- `app/errors.py` — generalized `RequestValidationError`/`StarletteHTTPException` handlers; already produce `VALIDATION_ERROR` (422) and `MALFORMED_JSON` (400) for any entity, no change needed
- `tests/conftest.py:47-64` — `seed_escalation` fixture helper, and the `client`/`conn` fixtures
- `tests/test_incidents.py:102-135` — `POST /incidents` test pattern (201 with server-assigned fields, missing-field 422, retrievable-immediately)
- `tests/test_db.py:33-51` — `next_incident_number` test pattern to mirror exactly for the escalation allocator

## Context Packets

### Task 1 Context
- Spec: `.context-index/specs/features/itsm-api/escalations-rev-2-create-escalation.spec.md` (BEH-9's server-assignment clause)
- Charter: `.context-index/specs/features/itsm-api/charter.md` (capability: Create Escalation)
- Source files: `app/db.py` (full, for `next_incident_number` pattern + insertion point), `tests/test_db.py` (full, for exact test pattern to mirror)

### Task 2 Context
- Spec: `.context-index/specs/features/itsm-api/escalations-rev-2-create-escalation.spec.md` (BEH-9 through BEH-13, Error Cases table, System Constitution Reference)
- Charter: `.context-index/specs/features/itsm-api/charter.md` (capability: Create Escalation; Interface Contracts: `POST /escalations`)
- Base spec: `.context-index/specs/features/itsm-api/escalations.spec.md` (Escalation domain shape, immutable-field precedent from `PATCH`)
- Source files: `app/models.py` (full), `app/routers/escalations.py` (full), `app/routers/incidents.py:123-145` (signature + body, `create_incident` reference), `app/errors.py` (full, to confirm no change needed), `tests/test_escalations.py` (full, for fixture/assertion conventions), `tests/test_incidents.py:102-135` (signature + body, `POST /incidents` test pattern)

## Parallelization

- Group A (independent): Task 1
- Group B (sequential): Task 2

Task 2 depends on Task 1 (it calls `next_escalation_number`), so it cannot start until Task 1's implementation step lands. Task 1 has no dependents besides Task 2, so there is no second independent group to run concurrently with it.

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | `next_escalation_number` allocator | small | unit | — | 0 create, 2 modify |
| 2 | `POST /escalations` endpoint | medium | unit | Task 1 | 0 create, 3 modify |

## Task Structure

### Task 1: `next_escalation_number` allocator [specialist: none]

**Charter capability:** Create Escalation
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/db.py` (add function after `next_incident_number`, line ~174)
- Test: `tests/test_db.py`

**Tests:** `tests/test_db.py` — extend (existing suite covers `next_incident_number`/`allocate_work_note_sys_id`; this task adds the escalation-number equivalent to the same file per this project's `per-behavior` granularity policy).

**Context to load:**
- `app/db.py:165-174` (`next_incident_number` — pattern to mirror exactly, same next-max-suffix derivation, different regex/prefix/width)
- `tests/test_db.py:33-51` (test pattern to mirror)

- [ ] **Write failing test**

```python
def test_next_escalation_number_starts_at_escalation_0001(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    assert next_escalation_number(conn) == "ESCALATION-0001"


def test_next_escalation_number_never_collides_with_existing_rows(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    conn.execute(
        "INSERT INTO escalations (number, account_id, summary, opened_at) "
        "VALUES ('ESCALATION-0412', 'ACC-1', 'x', '2026-01-01T00:00:00Z')"
    )
    conn.commit()
    assert next_escalation_number(conn) == "ESCALATION-0413"
```

Add `next_escalation_number` to the `from app.db import ...` line at the top of `tests/test_db.py`.

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_db.py -k escalation_number`
Expected: FAIL — `ImportError: cannot import name 'next_escalation_number' from 'app.db'`

- [ ] **Implement**

```python
def next_escalation_number(conn: sqlite3.Connection) -> str:
    """Server-assigned, ESCALATION-NNNN, guaranteed not to collide with any existing row
    (seeded or previously created) — derived from the current max suffix, mirroring
    next_incident_number's collision-proof scheme, sized to the existing 4-digit
    ESCALATION-04xx seed range."""
    max_seq = 0
    for row in conn.execute("SELECT number FROM escalations"):
        match = _ESCALATION_NUMBER_RE.match(row["number"])
        if match:
            max_seq = max(max_seq, int(match.group(1)))
    return f"ESCALATION-{max_seq + 1:04d}"
```

Add `_ESCALATION_NUMBER_RE = re.compile(r"^ESCALATION-(\d{4})$")` as a module-level constant next to the existing `_NUMBER_RE = re.compile(r"^TICKET-(\d{6})$")` (confirmed at `app/db.py:5`; `re` is already imported at `app/db.py:1` — do not re-import).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/test_db.py -k escalation_number`
Expected: PASS

- [ ] **Commit**

Branch (if not already created): `feat/escalation-create` (this session is already on this branch — do not create a new one)

```bash
git add app/db.py tests/test_db.py
git commit -m "feat(itsm-api): add next_escalation_number allocator"
```

---

### Task 2: `POST /escalations` endpoint [specialist: none]

**Depends on:** Task 1
**Charter capability:** Create Escalation
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `app/models.py` (add `EscalationCreate` after `EscalationRead`)
- Modify: `app/routers/escalations.py` (add `create_escalation` handler)
- Test: `tests/test_escalations.py`

**Tests:** `tests/test_escalations.py` — extend (existing suite covers `GET`/`PATCH /escalations`; this task adds six `POST` behavior tests — BEH-9 through BEH-13 plus the immediate-visibility postcondition — to the same file per this project's `per-behavior` granularity policy).

**Context to load:**
- `app/routers/incidents.py:123-145` (`create_incident` — pattern to mirror: allocate number/opened_at, insert, return 201 with full read model)
- `app/models.py:13-23` (`IncidentCreate` — Pydantic model pattern to mirror)
- `tests/test_incidents.py:102-135` (`POST /incidents` test pattern: 201 + server-assigned fields, missing-field 422 + persists-nothing assertion, immediately-retrievable)
- Spec Error Cases table and BEH-9 through BEH-13 (exact required/optional field list, silently-ignored `closed_at`)

- [ ] **Write failing test**

```python
def test_create_escalation_returns_201_with_server_assigned_fields(client):
    resp = client.post(
        "/escalations", json={"account_id": "ACC-1", "summary": "New escalation"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["number"].startswith("ESCALATION-")
    assert body["account_id"] == "ACC-1"
    assert body["summary"] == "New escalation"
    assert body["opened_at"] is not None
    assert body["incident_number"] is None
    assert body["owner"] is None
    assert body["closed_at"] is None


def test_create_escalation_stores_optional_incident_number_and_owner(client):
    resp = client.post(
        "/escalations",
        json={
            "account_id": "ACC-1",
            "summary": "New escalation",
            "incident_number": "TICKET-000123",
            "owner": "dana",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_number"] == "TICKET-000123"
    assert body["owner"] == "dana"


def test_create_escalation_ignores_closed_at_in_request_body(client):
    resp = client.post(
        "/escalations",
        json={
            "account_id": "ACC-1",
            "summary": "New escalation",
            "closed_at": "2026-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["closed_at"] is None


def test_create_escalation_missing_required_field_returns_422_and_creates_nothing(client):
    resp = client.post("/escalations", json={"summary": "No account"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "account_id" in body["message"]
    assert client.get("/escalations").json()["total"] == 0


def test_create_escalation_malformed_json_returns_400(client):
    resp = client.post(
        "/escalations",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "MALFORMED_JSON"
    assert client.get("/escalations").json()["total"] == 0


def test_create_escalation_immediately_visible_via_list_and_get(client):
    created = client.post(
        "/escalations", json={"account_id": "ACC-1", "summary": "New escalation"}
    ).json()
    number = created["number"]

    listing = client.get("/escalations").json()
    assert number in {item["number"] for item in listing["items"]}

    fetched = client.get(f"/escalations/{number}")
    assert fetched.status_code == 200
    assert fetched.json()["summary"] == "New escalation"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_escalations.py -k create_escalation`
Expected: FAIL — `404 Not Found` (no `POST /escalations` route registered yet) on the first test, or a collection error if the route is entirely absent from the router.

- [ ] **Implement**

In `app/models.py`, after `EscalationRead`:

```python
class EscalationCreate(BaseModel):
    account_id: str
    summary: str
    incident_number: str | None = None
    owner: str | None = None
```

In `app/routers/escalations.py`, import `next_escalation_number` from `app.db` and `EscalationCreate` from `app.models`, then add:

```python
@router.post("/escalations", response_model=EscalationRead, status_code=201)
def create_escalation(payload: EscalationCreate, request: Request):
    conn = request.app.state.db_conn
    number = next_escalation_number(conn)
    opened_at = datetime.now(timezone.utc).isoformat()

    conn.execute(
        """
        INSERT INTO escalations
            (number, incident_number, account_id, summary, opened_at, closed_at, owner)
        VALUES (?, ?, ?, ?, ?, NULL, ?)
        """,
        (number, payload.incident_number, payload.account_id, payload.summary, opened_at,
         payload.owner),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM escalations WHERE number = ?", (number,)).fetchone()
    return _row_to_escalation_read(row)
```

Add the `datetime`/`timezone` import at the top of `app/routers/escalations.py` if not already present (check first — `incidents.py` already imports these; `escalations.py` currently does not).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/test_escalations.py -k create_escalation`
Expected: PASS (all 6 new tests)

Then run the full suite to confirm no regressions: `python3 -m pytest -q`

- [ ] **Commit**

```bash
git add app/models.py app/routers/escalations.py tests/test_escalations.py
git commit -m "feat(itsm-api): add POST /escalations endpoint"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are recorded in the validation report (`.validate.md`), not in this plan.

Per `.context-index/governance/gates.yaml`:
- `test` (required, error): `python3 -m pytest -q`
- `lint` (required, error): `ruff check .`
- `test-js` (required, error): `node --test tests_js/**/*.test.js` — not touched by this plan (backend-only change), expected unaffected
- `e2e-smoke` (optional, warning): `python3 -m pytest -q tests_e2e/` — not extended by this plan; existing e2e escalation tests are unaffected
- `integration-test` — unwired (empty command), skipped
- All acceptance criteria from the spec satisfied (BEH-9 through BEH-13, plus the two immediate-visibility and no-collision criteria)
