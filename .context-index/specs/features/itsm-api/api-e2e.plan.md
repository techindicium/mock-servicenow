# Implementation Plan: End-to-end API test suite (real HTTP)

> **Methodology:** adev
> **Charter:** .context-index/specs/features/itsm-api/charter.md
> **Spec:** .context-index/specs/features/itsm-api/api-e2e.spec.md
> **Review:** PASS_WITH_NOTES (2026-09-07) — SA-1 (warning): BEH-4 and the Error Cases/Task Map
> "all three seeded discrepancies" language did not yet have a Behavior asserting the third
> discrepancy (resolved Incident, open `first_response` breach) over real HTTP. This plan closes
> that gap in Task 7.
> **Platform:** presumed FastAPI (uvicorn) over SQLite, Python 3.11, httpx, pytest — `platform-context.yaml`
> still has `framework: none` because no itsm-api code exists yet; this choice follows the
> constitution's "Patterns to Follow" (mirror `mock-jira`'s shape) and the charter's own framing.
> Confirm at implementation time against whatever the sibling specs' plans actually land.

**Goal:** Add a real-HTTP end-to-end test suite that starts the itsm-api application as its own
OS process (never in-process via FastAPI's `TestClient`) and drives every documented
Incident/WorkNote/Escalation/TaskSla/directory behavior — plus the PRD's analytics-parity filter
query, the documented error paths, the OpenAPI contract, and all three seeded discrepancies —
over a live socket, exactly as `portwell-assist`, `portwell-analytics`, or `portwell-knowledge`
would connect.

**Architecture:** A `tests_e2e/` directory sits alongside the fast, in-process `tests/` suites the
six sibling specs (`incident-lifecycle`, `work-notes`, `escalations`, `sla-records`,
`user-directory`, `fixture-seeding`) will create. Its core is a reusable
`start_itsm_api(tmp_path)` context manager in `tests_e2e/servers.py` — modeled directly on
`mock-jira`'s `tests_e2e/servers.py::start_issue_tracker_api` — that launches the real app as a
subprocess (`uvicorn app.main:app`, matching the `app/` module path already registered in
`manifest.yaml`) on an ephemeral `127.0.0.1` port, points `DATABASE_PATH` at a fresh temp file,
runs the documented seed command, polls `GET /` until healthy, yields the base URL, and tears the
process down afterward. This function stays framework-light (no pytest dependency) so it can be
reused directly by any future e2e-shaped spec in this repo (e.g. an `mcp-server` e2e suite that
wants to start the real itsm-api as its upstream dependency) exactly the way `mock-jira` designed
its own `servers.py` for reuse by sibling repos. `tests_e2e/conftest.py` wraps it in a
session-scoped `server` fixture for this suite's own shared-state tests; tests that need a truly
fresh, freshly-seeded database (BEH-1's fresh-seed assertion, the discrepancy-presence test) call
`start_itsm_api` directly with their own `tmp_path` instead of the shared fixture, so no other
test's writes contaminate the assertion.

**Dependency note (see Parallelization):** every test task in this plan asserts real behavior
served by a real running process with no mocks. None of them can pass — and most cannot even be
meaningfully written against confirmed file paths — until the `incident-lifecycle`, `work-notes`,
`escalations`, `sla-records`, `user-directory`, and `fixture-seeding` specs each have their own
plan implemented. This plan's own task order (TDD: write failing test, verify fail, implement,
verify pass, commit) still applies per task, but at the plan level this whole plan is gated on
that sibling work landing first, per the milestone ordering (those five specs are `milestone: mvp`
land in this repo, this spec is `milestone: v1.1`).

---

## File Structure

**Create:**
- `tests_e2e/__init__.py` — empty; package marker, matching `mock-jira`'s convention.
- `tests_e2e/servers.py` — the reusable `start_itsm_api(tmp_path)` context manager (subprocess
  launch, ephemeral port, seed invocation, health poll, teardown) and `E2EServerStartTimeout`.
- `tests_e2e/conftest.py` — session-scoped `server` fixture wrapping `start_itsm_api` with a
  `tmp_path_factory`-produced directory (fresh DB file per test *session*, per spec Preconditions).
- `tests_e2e/test_server_fixture.py` — direct test of the fixture contract (real OS process,
  ephemeral port, temp DB, seeded, polls `GET /`, yields a reachable base URL, tears down cleanly)
  and the `E2E_SERVER_START_TIMEOUT` error case.
- `tests_e2e/test_incident_crud_e2e.py` — BEH-1 (fresh-seed visibility) and BEH-2 (full Incident
  lifecycle: create → list/get with filters → patch state/priority/assigned_to/assignment_group).
- `tests_e2e/test_work_notes_e2e.py` — the list/add-work-notes portion of BEH-2.
- `tests_e2e/test_escalations_e2e.py` — the Escalation half of BEH-4 (ownerless escalations read
  correctly, no error).
- `tests_e2e/test_sla_e2e.py` — the TaskSla half of BEH-4 (`business_time_only: true` resolution
  records read correctly, no error).
- `tests_e2e/test_analytics_filter_e2e.py` — BEH-3, the PRD acceptance-criteria filter query
  (`GET /incidents?account_id=ACCOUNT-1001&opened_after=2026-08-01`), cross-checked against
  independently filtered fixture data fetched over the same live connection.
- `tests_e2e/test_seeded_discrepancies_e2e.py` — the discrepancy-presence test: all three seeded
  discrepancies (SLA business-hours/wall-clock disagreement, two ownerless Escalations, and the
  third discrepancy this plan adds per review note SA-1 — a resolved/closed Incident whose
  `first_response` TaskSla still shows `has_breached: true`), asserted present over real HTTP
  after a fresh seed. Fails loudly naming which discrepancy is missing
  (`E2E_DISCREPANCY_MISSING`).
- `tests_e2e/test_directory_e2e.py` — BEH-5 (`GET /users`, `GET /assignment_groups`).
- `tests_e2e/test_error_paths_e2e.py` — BEH-6 (404 `INCIDENT_NOT_FOUND`/`ESCALATION_NOT_FOUND`,
  422 `VALIDATION_ERROR` for invalid `state`/`priority`/`note_type`/`sla_definition`).
- `tests_e2e/test_openapi_e2e.py` — BEH-7 (`GET /openapi.json` lists every implemented route).
- `pytest.ini` — `testpaths = tests`, so the constitution's `test` gate (`python3 -m pytest -q`,
  no path argument) keeps discovering only the fast in-process suites and never recurses into
  `tests_e2e/` — mirrors `mock-jira`'s own isolation fix.
- `tests/test_pytest_config.py` — proves that isolation is real (Task 11).
- `tests/test_gates_config.py` — proves the `e2e-smoke` gate is defined correctly (Task 12); if a
  sibling plan already created this file for another purpose, extend it instead of recreating it.

**Modify:**
- `.context-index/governance/gates.yaml` — uncomment/complete the already-stubbed `e2e-smoke`
  gate entry (Task 12).

**Reference (read, do not modify) — anticipated paths, not yet created; confirm exact names
against whatever the sibling specs' plans actually land before writing each task's test:**
- `app/main.py` (`incident-lifecycle.plan.md` Task 1) — the module-level `app` object reads its
  SQLite path from the `DATABASE_PATH` env var (default `servicenow.db`), root route `GET /`
  (health check); no seed wiring — seeding is a separate, explicit step (see below).
- `app/seed.py` (`fixture-seeding.plan.md`'s `main()`) — `python -m app.seed`, the documented,
  explicitly-invoked seed command this fixture must invoke as its own subprocess call against the
  same `DATABASE_PATH`-pointed temp DB before starting the API process — never via an app-startup
  hook, per that plan's explicit design decision.
- `app/routers/incidents.py`, `.../work_notes.py` (nested under `/incidents/{number}/work_notes`),
  `.../escalations.py`, `.../sla.py`, `.../directory.py` (both `/users` and `/assignment_groups`,
  a single router file per `user-directory.plan.md`) — the seven documented endpoints.
- `.context-index/specs/features/itsm-api/incident-lifecycle.spec.md` — exact status codes,
  `VALIDATION_ERROR`/`INCIDENT_NOT_FOUND` bodies, `state`/`priority` enums.
- `.context-index/specs/features/itsm-api/work-notes.spec.md` — `note_type` enum,
  `INTERACTION-NNNNNNN` sys_id scheme, chronological ordering.
- `.context-index/specs/features/itsm-api/escalations.spec.md` — `ESCALATION_NOT_FOUND`,
  `open_only` filter, explicit-null `owner` semantics.
- `.context-index/specs/features/itsm-api/sla-records.spec.md` — `business_time_only` semantics,
  `breached`/`sla_definition` filters, empty-array-not-404 on unknown `incident_number`.
- `.context-index/specs/features/itsm-api/user-directory.spec.md` — `SysUser`/`AssignmentGroup`
  field shapes, the three fixed group names.
- `.context-index/specs/features/itsm-api/fixture-seeding.spec.md` — exact seeded row counts
  (1,307 Incidents / 2,614 WorkNotes / 5 Escalations, two ownerless), determinism guarantees, and
  the fact that discrepancy identifiers are not individually named in any spec — this suite must
  discover them by querying, never by hardcoding a specific seeded `number`.
- `mock-jira/.context-index/specs/features/issue-tracker-api/api-e2e.plan.md` — pattern reference
  for `servers.py`, `conftest.py`, gate isolation, and gate wiring.
- `governance/gates.yaml` — existing `test`/`lint`/`integration-test` gate shapes and the
  already-commented `e2e-smoke` stub this plan completes.

---

## Context Packets

No `source-manifest.files[]` exists on this spec yet (no code has been written for this module).
Context packets fall back to the charter's Capability Map, the sibling specs' behavioral
contracts, and `mock-jira`'s stamped e2e plan as a structural pattern reference.

### Task 1 Context
- Spec: `api-e2e.spec.md` — Preconditions, Error Cases (`E2E_SERVER_START_TIMEOUT` row)
- Charter: `charter.md` (capability: "End-to-end API test suite"), Interface Contracts table
  (all seven endpoints), Quality Attributes (localhost-only binding)
- Sibling spec: `fixture-seeding.spec.md` — the documented seed command this fixture must invoke
- Pattern: `mock-jira/.../api-e2e.plan.md` Task 1 (`servers.py`, `conftest.py`)
- Constitution: "Fixture-backed, offline only" (bind to `127.0.0.1` only)

### Task 2 Context
- Spec: `api-e2e.spec.md` — BEH-1, BEH-2 (incident portion)
- Sibling spec: `incident-lifecycle.spec.md` — BEH-1 through BEH-9, all five endpoints, error codes
- Charter: capabilities "List/get Incident", "Create/update Incident"

### Task 3 Context
- Spec: `api-e2e.spec.md` — BEH-2 (work-notes portion)
- Sibling spec: `work-notes.spec.md` — BEH-1 through BEH-7, `INTERACTION-NNNNNNN` scheme
- Charter: capability "List/add Work Notes"

### Task 4 Context
- Spec: `api-e2e.spec.md` — BEH-4 (escalation half)
- Sibling spec: `escalations.spec.md` — BEH-1, BEH-4, BEH-7 (null-owner semantics)
- Constitution: Principle 6 ("two ownerless escalations... must persist across reseeds")

### Task 5 Context
- Spec: `api-e2e.spec.md` — BEH-4 (SLA half)
- Sibling spec: `sla-records.spec.md` — BEH-7, Preconditions (`business_time_only` semantics)
- Constitution: Principle 6 (SLA business-hours/wall-clock discrepancy)

### Task 6 Context
- Spec: `api-e2e.spec.md` — BEH-3
- Sibling spec: `incident-lifecycle.spec.md` — BEH-2 (`account_id`, `opened_after` filter
  semantics, inclusive/exclusive ISO comparison)
- Charter Business Intent: this is the exact query PRD.md's Acceptance section names

### Task 7 Context
- Spec: `api-e2e.spec.md` — BEH-4, Error Cases (`E2E_DISCREPANCY_MISSING` row), Actionable Task
  Map ("Discrepancy-presence e2e test")
- Review: `api-e2e.review.md` SA-1 — the exact gap this task closes (third discrepancy)
- Sibling spec: `fixture-seeding.spec.md` — BEH-5, Postconditions (all three discrepancies exact
  wording: SLA business-hours/wall-clock, two ownerless escalations, resolved/closed Incidents
  with an open `first_response` breach)
- Constitution: Principle 6 (full text, all three discrepancies)

### Task 8 Context
- Spec: `api-e2e.spec.md` — BEH-5
- Sibling spec: `user-directory.spec.md` — BEH-1 through BEH-4, field schema for `SysUser`/
  `AssignmentGroup` (this spec is the schema's sole authority — no PRD.md field table exists)

### Task 9 Context
- Spec: `api-e2e.spec.md` — BEH-6, Error Cases table (all rows)
- Sibling specs: `incident-lifecycle.spec.md`, `escalations.spec.md`, `work-notes.spec.md`,
  `sla-records.spec.md` — each spec's own Error Cases table (404/422 bodies and codes)

### Task 10 Context
- Spec: `api-e2e.spec.md` — BEH-7
- Charter: Interface Contracts table (every route that must appear in `doc["paths"]`)

### Task 11 Context
- Spec: `api-e2e.spec.md` — Architecture rationale (fast-gate isolation)
- Pattern: `mock-jira/.../api-e2e.plan.md` Task 6
- Reference: `governance/gates.yaml` `test` gate command (no path argument)

### Task 12 Context
- Spec: `api-e2e.spec.md` — Actionable Task Map is silent on gate wiring, but `governance/
  gates.yaml`'s existing commented `e2e-smoke` stub and the constitution's Quality Gates note
  ("No integration-test or e2e command yet — seeded once this repo has one") both anticipate it
- Pattern: `mock-jira/.../api-e2e.plan.md` Task 7

---

## Parallelization

- Group A (sequential): Task 1 → Task 11 → Task 12
- Group B (independent): Task 2
- Group C (independent): Task 3
- Group D (independent): Task 4
- Group E (independent): Task 5
- Group F (independent): Task 6
- Group G (independent): Task 7
- Group H (independent): Task 8
- Group I (independent): Task 9
- Group J (independent): Task 10

Groups B through J each depend only on Task 1 (see each task's "Depends on" annotation) and can
run in parallel with each other; none of them touches a file another group touches. Task 11
additionally depends on Tasks 2 through 10 having landed (it proves real exclusion of every
`tests_e2e/` file those tasks create, not just Task 1's fixture), and Task 12 depends on Task 11.
Group A's arrows represent that tail dependency chain, not a file-overlap constraint.

At the whole-plan level (outside this grammar, prose only): none of Task 1 through Task 12 can
be *implemented* (its "Implement" step run against real code) until the `incident-lifecycle`,
`work-notes`, `escalations`, `sla-records`, `user-directory`, and `fixture-seeding` specs each
have their own plan implemented — see the plan header's Dependency note.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Real-server-process fixture | medium | unit | — | 4 create, 0 modify |
| 2 | Incident CRUD e2e test | medium | unit | Task 1 | 1 create, 0 modify |
| 3 | Work-notes e2e test | small | unit | Task 1 | 1 create, 0 modify |
| 4 | Escalations e2e test | small | unit | Task 1 | 1 create, 0 modify |
| 5 | SLA e2e test | small | unit | Task 1 | 1 create, 0 modify |
| 6 | Analytics-parity filter query e2e test | small | unit | Task 1 | 1 create, 0 modify |
| 7 | Seeded-discrepancies presence e2e test | medium | unit | Task 1 | 1 create, 0 modify |
| 8 | Directory e2e test | small | unit | Task 1 | 1 create, 0 modify |
| 9 | Error-path e2e test | small | unit | Task 1 | 1 create, 0 modify |
| 10 | OpenAPI e2e test | small | unit | Task 1 | 1 create, 0 modify |
| 11 | Isolate `tests_e2e/` from the fast gate | small | unit | Task 2-10 | 2 create, 0 modify |
| 12 | Wire the `e2e-smoke` gate | small | unit | Task 11 | 1 create, 1 modify |

All twelve tasks resolve to the `unit` strategy (source: fallback — no `test_strategy` in the
spec's frontmatter, no matching `manifest.yaml` glob rule). Strategy Summary and Test
Infrastructure Requirements sections are omitted per the plan template (all-unit, no
`infra_requirements:` on the spec, no external systems beyond the locally-started process itself).

---

## Task Structure

> Task status lives in the spec's lifecycle event log (`plan_task` events), not in the `- [ ]`
> checkboxes below — those are authoring guides only.

### Task 1: Real-server-process fixture [specialist: none]

**Charter capability:** End-to-end API test suite
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `tests_e2e/__init__.py`
- Create: `tests_e2e/servers.py`
- Create: `tests_e2e/conftest.py`
- Test: `tests_e2e/test_server_fixture.py`

**Tests:** `tests_e2e/test_server_fixture.py` — new suite (per-behavior granularity: covers the
Preconditions/Error-Cases contract of the reusable fixture itself, not one of BEH-1..7).

**Context to load:** `app/main.py` (once it exists — root route, `DATABASE_PATH` convention),
`fixture-seeding.spec.md` (seed command entrypoint), `mock-jira`'s `tests_e2e/servers.py` pattern.

- [ ] **Write failing test**

```python
# tests_e2e/test_server_fixture.py
import httpx
import pytest

from tests_e2e.servers import E2EServerStartTimeout, start_itsm_api


def test_start_itsm_api_yields_reachable_seeded_base_url(tmp_path):
    with start_itsm_api(tmp_path) as base_url:
        resp = httpx.get(base_url + "/", timeout=5)
        assert resp.status_code == 200
        # Seeded before yielding — a fresh server must already carry fixture data.
        incidents = httpx.get(base_url + "/incidents", timeout=5).json()
        assert len(incidents.get("items", incidents)) > 0


def test_start_itsm_api_tears_down_process_on_exit(tmp_path):
    with start_itsm_api(tmp_path) as base_url:
        pass
    with pytest.raises(httpx.ConnectError):
        httpx.get(base_url + "/", timeout=1)


def test_start_itsm_api_raises_e2e_server_start_timeout_on_unhealthy_startup(tmp_path):
    not_a_dir = tmp_path / "not_a_directory"
    not_a_dir.write_text("this is a file, not a directory, so app startup fails fast")

    with pytest.raises(E2EServerStartTimeout) as exc_info:
        with start_itsm_api(not_a_dir):
            pass  # pragma: no cover - should never be reached

    message = str(exc_info.value)
    assert "startup timeout" in message  # names the timeout
    assert "Last output" in message      # names the last-seen process output
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_server_fixture.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'tests_e2e.servers'`.

- [ ] **Implement**

`tests_e2e/servers.py` — `start_itsm_api(tmp_path)` context manager, closely following
`mock-jira`'s `start_issue_tracker_api`: allocate a free `127.0.0.1` port, point `DATABASE_PATH`
at `tmp_path / "e2e.db"`, run the documented seed command (`python -m app.seed`, with
`DATABASE_PATH` set the same way) against that path as its own subprocess call **before** starting
the API process — `fixture-seeding.plan.md`'s Architecture section is explicit that seeding is
never wired into `app/main.py`'s startup, by design (a departure from the `mock-jira` exemplar
this plan otherwise mirrors), so this fixture must invoke it separately, not rely on any
app-startup seed hook — then launch `uvicorn app.main:app` as a subprocess, poll `GET /` until it
answers `200` or the `_STARTUP_TIMEOUT_SECONDS` budget (10s) is exhausted, naming the timeout and
last-seen process output on failure (`E2EServerStartTimeout`), yield the base URL, then
terminate/kill the process in a `finally` block guarded by a liveness check. `tests_e2e/conftest.py`
wraps this in a session-scoped `server` fixture using `tmp_path_factory.mktemp(...)`.
`tests_e2e/__init__.py` is empty.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_server_fixture.py`
Expected: PASS

- [ ] **Commit**

Branch (if not already created): `feat/itsm-api/e2e-testing`

```bash
git add tests_e2e/__init__.py tests_e2e/servers.py tests_e2e/conftest.py tests_e2e/test_server_fixture.py
git commit -m "feat(itsm-api): add reusable real-server-process e2e fixture"
```

### Task 2: Incident CRUD e2e test [specialist: none]

**Charter capability:** List/get Incident, Create/update Incident
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_incident_crud_e2e.py`

**Tests:** `tests_e2e/test_incident_crud_e2e.py` — new suite (BEH-1, BEH-2 incident portion).

**Context to load:** `incident-lifecycle.spec.md` (full — all nine behaviors, error codes).

- [ ] **Write failing test**

```python
# tests_e2e/test_incident_crud_e2e.py
import httpx

from tests_e2e.servers import start_itsm_api


def test_fresh_seed_incidents_visible_over_real_http(tmp_path):
    # BEH-1: isolated fresh server, not the shared session fixture — this asserts
    # seed-then-serve, not just that some incident happens to exist.
    with start_itsm_api(tmp_path) as base_url:
        with httpx.Client(base_url=base_url, timeout=5) as client:
            resp = client.get("/incidents")
            assert resp.status_code == 200
            body = resp.json()
            items = body.get("items", body)
            assert len(items) > 0


def test_full_incident_lifecycle_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        created = client.post(
            "/incidents",
            json={
                "account_id": "ACCOUNT-1001",
                "category": "network",
                "short_description": "e2e incident",
                "description": "created by the e2e suite",
                "state": "new",
                "priority": 3,
            },
        )
        assert created.status_code == 201
        incident = created.json()
        number = incident["number"]
        assert incident["escalated"] is False
        assert incident["assigned_to"] is None

        fetched = client.get(f"/incidents/{number}")
        assert fetched.status_code == 200
        assert fetched.json()["number"] == number

        listed = client.get("/incidents", params={"account_id": "ACCOUNT-1001"})
        assert any(i["number"] == number for i in listed.json().get("items", listed.json()))

        # BEH-8: unguarded patch — no permission/business-rule check on any transition.
        patched = client.patch(
            f"/incidents/{number}",
            json={
                "state": "resolved",
                "priority": 1,
                "assigned_to": "Rui Bastos",
                "assignment_group": "Support Tier 1",
            },
        )
        assert patched.status_code == 200
        updated = patched.json()
        assert updated["state"] == "resolved"
        assert updated["priority"] == 1
        assert updated["assigned_to"] == "Rui Bastos"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_incident_crud_e2e.py`
Expected: FAIL — `fixture 'server' not found` before Task 1 lands, or a real assertion/connection
failure once Task 1 is in place but the Incident endpoints don't exist yet (the sibling
`incident-lifecycle` plan's own responsibility, not this task's).

- [ ] **Implement**

No production code changes expected — `POST/GET/PATCH /incidents` are the `incident-lifecycle`
spec's responsibility. This task's own deliverable is the test file; it should go green as soon
as Task 1's fixture and the sibling plan's Incident endpoints are both in place. If this test
still fails once both are done, the gap is a real contract mismatch worth a bug report against
`incident-lifecycle`, not a change to this task.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_incident_crud_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_incident_crud_e2e.py
git commit -m "test(itsm-api): add real-HTTP Incident CRUD e2e coverage (BEH-1, BEH-2)"
```

### Task 3: Work-notes e2e test [specialist: none]

**Charter capability:** List/add Work Notes
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_work_notes_e2e.py`

**Tests:** `tests_e2e/test_work_notes_e2e.py` — new suite (BEH-2 work-notes portion).

**Context to load:** `work-notes.spec.md` (full).

- [ ] **Write failing test**

```python
# tests_e2e/test_work_notes_e2e.py
import httpx


def test_work_notes_list_and_add_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        incident = client.post(
            "/incidents",
            json={
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": "e2e work note incident",
                "description": "for work-note e2e coverage",
                "state": "new", "priority": 2,
            },
        ).json()
        number = incident["number"]

        # BEH-4: unguarded authorship — accepts "assist" with no check.
        created = client.post(
            f"/incidents/{number}/work_notes",
            json={"created_by": "assist", "note_type": "comment", "body": "e2e note"},
        )
        assert created.status_code == 201
        note = created.json()
        assert note["incident_number"] == number
        assert "sys_id" in note

        listed = client.get(f"/incidents/{number}/work_notes")
        assert listed.status_code == 200
        notes = listed.json().get("items", listed.json())
        assert any(n["sys_id"] == note["sys_id"] for n in notes)

        # Posting a work note never mutates the parent Incident's state.
        still_new = client.get(f"/incidents/{number}").json()
        assert still_new["state"] == "new"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_work_notes_e2e.py`
Expected: FAIL — `fixture 'server' not found` before Task 1, or a real failure before the
`work-notes` and `incident-lifecycle` sibling plans land.

- [ ] **Implement**

No production code changes expected — the work-notes endpoints are the `work-notes` spec's
responsibility.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_work_notes_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_work_notes_e2e.py
git commit -m "test(itsm-api): add real-HTTP work-notes e2e coverage (BEH-2)"
```

### Task 4: Escalations e2e test [specialist: none]

**Charter capability:** List/get/update Escalations
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_escalations_e2e.py`

**Tests:** `tests_e2e/test_escalations_e2e.py` — new suite (BEH-4 escalation half).

**Context to load:** `escalations.spec.md` (full — especially BEH-4, BEH-7 null-owner semantics).

- [ ] **Write failing test**

```python
# tests_e2e/test_escalations_e2e.py
import httpx


def test_ownerless_escalations_read_correctly_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/escalations")
        assert resp.status_code == 200
        escalations = resp.json().get("items", resp.json())
        assert len(escalations) > 0

        ownerless = [e for e in escalations if e["owner"] is None]
        assert len(ownerless) >= 1, (
            "expected at least one seeded ownerless Escalation (owner: null) — "
            "this is a load-bearing seeded discrepancy, not an error state"
        )

        one = client.get(f"/escalations/{ownerless[0]['number']}")
        assert one.status_code == 200
        assert one.json()["owner"] is None


def test_open_only_filter_excludes_closed_escalations(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        open_ones = client.get("/escalations", params={"open_only": "true"}).json()
        items = open_ones.get("items", open_ones)
        assert all(e["closed_at"] is None for e in items)
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_escalations_e2e.py`
Expected: FAIL — before Task 1 and the `escalations`/`fixture-seeding` sibling plans land.

- [ ] **Implement**

No production code changes expected — Escalation endpoints and seeded ownerless rows are the
`escalations`/`fixture-seeding` specs' responsibility.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_escalations_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_escalations_e2e.py
git commit -m "test(itsm-api): add real-HTTP Escalation e2e coverage (BEH-4)"
```

### Task 5: SLA e2e test [specialist: none]

**Charter capability:** List SLA records
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_sla_e2e.py`

**Tests:** `tests_e2e/test_sla_e2e.py` — new suite (BEH-4 SLA half).

**Context to load:** `sla-records.spec.md` (full — especially BEH-7, `business_time_only`).

- [ ] **Write failing test**

```python
# tests_e2e/test_sla_e2e.py
import httpx


def test_business_time_only_resolution_records_read_correctly_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/sla", params={"sla_definition": "resolution"})
        assert resp.status_code == 200
        records = resp.json().get("items", resp.json())
        assert len(records) > 0
        # Per sla-records.spec.md BEH-7: true for every resolution-definition record.
        assert all(r["business_time_only"] is True for r in records)


def test_unknown_incident_number_filter_returns_empty_array_not_404(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/sla", params={"incident_number": "TICKET-999999999"})
        assert resp.status_code == 200
        assert resp.json().get("items", resp.json()) == []
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_sla_e2e.py`
Expected: FAIL — before Task 1 and the `sla-records`/`fixture-seeding` sibling plans land.

- [ ] **Implement**

No production code changes expected — `GET /sla` and the derived `business_time_only` values are
the `sla-records`/`fixture-seeding` specs' responsibility.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_sla_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_sla_e2e.py
git commit -m "test(itsm-api): add real-HTTP SLA e2e coverage (BEH-4)"
```

### Task 6: Analytics-parity filter query e2e test [specialist: none]

**Charter capability:** List/get Incident
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_analytics_filter_e2e.py`

**Tests:** `tests_e2e/test_analytics_filter_e2e.py` — new suite (BEH-3, the PRD
acceptance-criteria filter query).

**Context to load:** `incident-lifecycle.spec.md` BEH-2 (filter semantics: inclusive/exclusive
ISO comparison on `opened_at`); charter Business Intent (this is the exact query PRD.md names).

- [ ] **Write failing test**

```python
# tests_e2e/test_analytics_filter_e2e.py
import httpx


def test_account_and_opened_after_filter_matches_independent_fixture_filtering(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        filtered_resp = client.get(
            "/incidents",
            params={"account_id": "ACCOUNT-1001", "opened_after": "2026-08-01"},
        )
        assert filtered_resp.status_code == 200
        filtered_numbers = {
            i["number"] for i in filtered_resp.json().get("items", filtered_resp.json())
        }

        # Independently filter the same seeded data by paging through the full,
        # unfiltered set and applying the same predicate in Python — the same way
        # the analytics warehouse would compute this set from a raw extract. The
        # canonical envelope (incident-lifecycle.plan.md Task 1) is
        # {"items", "page", "page_size", "total"} — no "has_more" field — so
        # pagination continues while fewer rows have been seen than "total".
        expected_numbers = set()
        seen = 0
        page = 1
        while True:
            page_resp = client.get(
                "/incidents", params={"account_id": "ACCOUNT-1001", "page": page}
            )
            body = page_resp.json()
            items = body["items"]
            if not items:
                break
            for incident in items:
                if incident["opened_at"] >= "2026-08-01":
                    expected_numbers.add(incident["number"])
            seen += len(items)
            if seen >= body["total"]:
                break
            page += 1
            if page > 200:  # safety valve against an unbounded loop
                raise AssertionError("pagination did not terminate")

        assert filtered_numbers == expected_numbers
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_analytics_filter_e2e.py`
Expected: FAIL — before Task 1 and the `incident-lifecycle`/`fixture-seeding` sibling plans land.

- [ ] **Implement**

No production code changes expected — the `account_id`/`opened_after` filter combination is the
`incident-lifecycle` spec's responsibility (BEH-2).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_analytics_filter_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_analytics_filter_e2e.py
git commit -m "test(itsm-api): add real-HTTP analytics-parity filter e2e coverage (BEH-3)"
```

### Task 7: Seeded-discrepancies presence e2e test [specialist: none]

**Charter capability:** End-to-end API test suite (guards Seed fixture data)
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_seeded_discrepancies_e2e.py`

**Tests:** `tests_e2e/test_seeded_discrepancies_e2e.py` — new suite. Covers all three seeded
discrepancies, including the third one this plan adds per review note SA-1: a resolved/closed
Incident whose `first_response` TaskSla still shows `has_breached: true`. None of the three
discrepancies has an individually-named seeded identifier in any spec, so this test discovers
each one by querying rather than hardcoding a specific `number` — that also makes it robust
against a reseed reordering rows, which is exactly what this test guards against
(`E2E_DISCREPANCY_MISSING`).

**Context to load:** `api-e2e.review.md` (SA-1, full text), `fixture-seeding.spec.md` BEH-5,
constitution Principle 6 (full text — all three discrepancies named).

- [ ] **Write failing test**

```python
# tests_e2e/test_seeded_discrepancies_e2e.py
import httpx


def _all_pages(client, path, **params):
    # Canonical envelope (incident-lifecycle.plan.md Task 1) is
    # {"items", "page", "page_size", "total"} — no "has_more" field — so pagination
    # continues while fewer rows have been seen than "total".
    items = []
    page = 1
    while True:
        resp = client.get(path, params={**params, "page": page})
        body = resp.json()
        page_items = body["items"]
        if not page_items:
            break
        items.extend(page_items)
        if len(items) >= body["total"]:
            break
        page += 1
        if page > 500:
            raise AssertionError(f"pagination over {path} did not terminate")
    return items


def test_sla_business_hours_wall_clock_discrepancy_present(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resolution_records = _all_pages(client, "/sla", sla_definition="resolution")
        assert len(resolution_records) > 0, "E2E_DISCREPANCY_MISSING: no resolution SLA records"
        assert all(r["business_time_only"] is True for r in resolution_records), (
            "E2E_DISCREPANCY_MISSING: SLA business-hours/wall-clock discrepancy — "
            "expected every resolution-definition record to have business_time_only: true"
        )


def test_two_ownerless_escalations_present(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        escalations = _all_pages(client, "/escalations")
        ownerless = [e for e in escalations if e["owner"] is None]
        assert len(ownerless) >= 2, (
            "E2E_DISCREPANCY_MISSING: expected at least two ownerless Escalations "
            f"(owner: null), found {len(ownerless)}"
        )


def test_resolved_incident_with_open_first_response_breach_present(server):
    # Third discrepancy (review note SA-1): a resolved/closed Incident whose
    # first_response TaskSla still shows has_breached: true.
    with httpx.Client(base_url=server, timeout=5) as client:
        breached_first_response = _all_pages(
            client, "/sla", sla_definition="first_response", breached="true"
        )
        assert len(breached_first_response) > 0, (
            "E2E_DISCREPANCY_MISSING: no breached first_response SLA records at all"
        )

        breached_incident_numbers = {r["incident_number"] for r in breached_first_response}
        found = False
        for number in breached_incident_numbers:
            incident = client.get(f"/incidents/{number}").json()
            if incident["state"] in ("resolved", "closed"):
                found = True
                break

        assert found, (
            "E2E_DISCREPANCY_MISSING: expected at least one resolved-or-closed Incident "
            "whose first_response TaskSla still has_breached: true"
        )
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_seeded_discrepancies_e2e.py`
Expected: FAIL — before Task 1 and the `sla-records`/`escalations`/`incident-lifecycle`/
`fixture-seeding` sibling plans land.

- [ ] **Implement**

No production code changes expected — all three discrepancies are seeded by the
`fixture-seeding` spec's implementation and served by the `sla-records`/`escalations`/
`incident-lifecycle` endpoints. If any one assertion fails once every sibling plan is
implemented, that is exactly the `E2E_DISCREPANCY_MISSING` condition this suite exists to catch —
raise it as a bug against the seeding implementation, never "fix" it by loosening this test
(constitution Principle 6: these are load-bearing, not bugs, to be preserved not corrected).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_seeded_discrepancies_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_seeded_discrepancies_e2e.py
git commit -m "test(itsm-api): add real-HTTP seeded-discrepancies presence coverage, closing review note SA-1"
```

### Task 8: Directory e2e test [specialist: none]

**Charter capability:** List users and assignment groups
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_directory_e2e.py`

**Tests:** `tests_e2e/test_directory_e2e.py` — new suite (BEH-5).

**Context to load:** `user-directory.spec.md` (full — this spec is the sole schema authority for
`SysUser`/`AssignmentGroup`).

- [ ] **Write failing test**

```python
# tests_e2e/test_directory_e2e.py
import httpx


def test_users_and_assignment_groups_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        groups_resp = client.get("/assignment_groups")
        assert groups_resp.status_code == 200
        group_names = {g["name"] for g in groups_resp.json().get("items", groups_resp.json())}
        assert group_names == {"Support Tier 1", "Support Tier 2", "Solution Consultants"}

        users_resp = client.get("/users")
        assert users_resp.status_code == 200
        users = users_resp.json().get("items", users_resp.json())
        assert len(users) > 0
        for user in users:
            if user.get("assignment_group") is not None:
                assert user["assignment_group"] in group_names
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_directory_e2e.py`
Expected: FAIL — before Task 1 and the `user-directory` sibling plan lands.

- [ ] **Implement**

No production code changes expected — `GET /users` and `GET /assignment_groups` are the
`user-directory` spec's responsibility.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_directory_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_directory_e2e.py
git commit -m "test(itsm-api): add real-HTTP directory e2e coverage (BEH-5)"
```

### Task 9: Error-path e2e test [specialist: none]

**Charter capability:** List/get Incident, List/get/update Escalations, List SLA records
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_error_paths_e2e.py`

**Tests:** `tests_e2e/test_error_paths_e2e.py` — new suite (BEH-6, all documented error rows).

**Context to load:** the Error Cases table in each of `incident-lifecycle.spec.md`,
`work-notes.spec.md`, `escalations.spec.md`, `sla-records.spec.md`.

- [ ] **Write failing test**

```python
# tests_e2e/test_error_paths_e2e.py
import httpx


def test_unknown_incident_number_returns_404(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/incidents/TICKET-000000")
        assert resp.status_code == 404
        assert resp.json()["code"] == "INCIDENT_NOT_FOUND"


def test_unknown_escalation_number_returns_404(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/escalations/ESCALATION-0000")
        assert resp.status_code == 404
        assert resp.json()["code"] == "ESCALATION_NOT_FOUND"


def test_invalid_state_on_create_returns_422(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.post(
            "/incidents",
            json={
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": "bad state", "description": "e2e",
                "state": "not-a-real-state", "priority": 2,
            },
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"


def test_invalid_priority_on_patch_returns_422(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        incident = client.post(
            "/incidents",
            json={
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": "for patch", "description": "e2e",
                "state": "new", "priority": 2,
            },
        ).json()
        resp = client.patch(f"/incidents/{incident['number']}", json={"priority": 99})
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"


def test_invalid_note_type_returns_422(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        incident = client.post(
            "/incidents",
            json={
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": "for note", "description": "e2e",
                "state": "new", "priority": 2,
            },
        ).json()
        resp = client.post(
            f"/incidents/{incident['number']}/work_notes",
            json={"created_by": "assist", "note_type": "not-a-real-type", "body": "x"},
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"


def test_invalid_sla_definition_returns_422(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/sla", params={"sla_definition": "not-a-real-definition"})
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_error_paths_e2e.py`
Expected: FAIL — before Task 1 and every relevant sibling plan lands.

- [ ] **Implement**

No production code changes expected — all six error paths are each sibling spec's own
responsibility.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_error_paths_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_error_paths_e2e.py
git commit -m "test(itsm-api): add real-HTTP error-path e2e coverage (BEH-6)"
```

### Task 10: OpenAPI e2e test [specialist: none]

**Charter capability:** OpenAPI contract
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_openapi_e2e.py`

**Tests:** `tests_e2e/test_openapi_e2e.py` — new suite (BEH-7).

**Context to load:** charter Interface Contracts table (every route that must appear).

- [ ] **Write failing test**

```python
# tests_e2e/test_openapi_e2e.py
import httpx

EXPECTED_PATHS = {
    "/", "/incidents", "/incidents/{number}",
    "/incidents/{number}/work_notes",
    "/escalations", "/escalations/{number}",
    "/sla", "/users", "/assignment_groups",
}


def test_openapi_json_lists_every_implemented_route_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        doc = resp.json()
        documented_paths = set(doc["paths"].keys())
        missing = EXPECTED_PATHS - documented_paths
        assert not missing, f"OpenAPI document is missing routes: {missing}"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_openapi_e2e.py`
Expected: FAIL — before Task 1 and the full endpoint surface lands.

- [ ] **Implement**

No production code changes expected — FastAPI generates `/openapi.json` automatically from the
routes each sibling spec's plan implements.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_openapi_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_openapi_e2e.py
git commit -m "test(itsm-api): add real-HTTP OpenAPI e2e coverage (BEH-7)"
```

### Task 11: Isolate `tests_e2e/` from the fast test gate [specialist: none]

**Charter capability:** End-to-end API test suite (supports the "separately gated" design intent)
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 2, Task 3, Task 4, Task 5, Task 6, Task 7, Task 8, Task 9, Task 10
**Files:**
- Create: `pytest.ini`
- Test: `tests/test_pytest_config.py`

**Tests:** `tests/test_pytest_config.py` — new suite, in the fast `tests/` tree (this checks
discovery configuration, not e2e behavior).

**Context to load:** `governance/gates.yaml` `test` gate command (no path argument today);
`mock-jira/.../api-e2e.plan.md` Task 6 (identical pattern).

- [ ] **Write failing test**

```python
# tests/test_pytest_config.py
import subprocess
import sys


def test_bare_pytest_collection_excludes_tests_e2e():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--collect-only"],
        capture_output=True, text=True, cwd=".",
    )
    assert "tests_e2e" not in result.stdout
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_pytest_config.py`
Expected: FAIL — with Tasks 2-10 already landed and no `pytest.ini` yet, bare collection includes
`tests_e2e` entries in stdout, so the `not in` assertion fails. If a sibling plan already created
`pytest.ini` for its own reasons, extend it rather than overwrite it, and adjust this test's
verify-fail expectation accordingly (it may already partially pass).

- [ ] **Implement**

```ini
# pytest.ini
[pytest]
testpaths = tests
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/test_pytest_config.py`
Expected: PASS. Also re-run the full fast gate to confirm nothing in `tests/` was dropped:
`python3 -m pytest -q`.

- [ ] **Commit**

```bash
git add pytest.ini tests/test_pytest_config.py
git commit -m "chore(itsm-api): restrict bare pytest discovery to tests/, excluding tests_e2e/"
```

### Task 12: Wire the `e2e-smoke` gate [specialist: none]

**Charter capability:** End-to-end API test suite
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 11
**Files:**
- Modify: `.context-index/governance/gates.yaml` (uncomment/complete the existing `e2e-smoke`
  stub, after the `integration-test` entry)
- Test: `tests/test_gates_config.py`

**Tests:** `tests/test_gates_config.py` — new suite, in `tests/` (checks a governance config
file, not e2e runtime behavior). If a sibling plan already created this file, extend it.

**Context to load:** `governance/gates.yaml` (full — the already-commented `e2e-smoke` stub is
the nearest precedent, already shaped correctly for this task to complete).

- [ ] **Write failing test**

```python
# tests/test_gates_config.py
from pathlib import Path

import yaml


def test_e2e_smoke_gate_is_defined_correctly():
    doc = yaml.safe_load(Path(".context-index/governance/gates.yaml").read_text())
    gates = {g["id"]: g for g in doc["gates"]}
    assert "e2e-smoke" in gates
    gate = gates["e2e-smoke"]
    assert gate["tier"] == "e2e"
    assert gate["command"] == ["python3", "-m", "pytest", "-q", "tests_e2e/"]
    assert gate.get("required") is False or gate.get("severity") == "warning"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_gates_config.py`
Expected: FAIL — `KeyError: 'e2e-smoke'` (still commented out).

- [ ] **Implement**

Uncomment and complete the existing stub in `.context-index/governance/gates.yaml`, after the
`integration-test` entry:

```yaml
  - id: e2e-smoke
    name: E2E API Smoke Suite
    kind: deterministic
    tier: e2e
    command: [python3, -m, pytest, -q, tests_e2e/]
    scope: project
    required: false
    severity: warning
    triggers:
      - post-implement
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/test_gates_config.py`
Expected: PASS

- [ ] **Commit**

```bash
git add .context-index/governance/gates.yaml tests/test_gates_config.py
git commit -m "feat(itsm-api): wire e2e-smoke gate for tests_e2e/ (tier: e2e, warning)"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are
recorded in the validation report (`.validate.md`), not in this plan.

`governance/gates.yaml` defines the deterministic gates for this project — used here instead of
constitution Quality Gates, per plan template precedence:

| Gate | Tier | Command | Severity |
|------|------|---------|----------|
| `test` | fast | `python3 -m pytest -q` | error |
| `lint` | fast | `ruff check .` | error |
| `integration-test` | integration | *(unwired — `command: ""`)* | error (skipped, no command) |
| `e2e-smoke` | e2e | `python3 -m pytest -q tests_e2e/` | warning *(added by Task 12)* |

- The `test` gate must keep passing with `tests_e2e/` excluded from its bare-invocation discovery
  scope (Task 11) — this is the load-bearing invariant this plan protects.
- `e2e-smoke` is `severity: warning` / `required: false`, matching the e2e-tier default already
  stubbed in `governance/gates.yaml` and this repo's overall lightweight governance posture
  (`risk-policies.yaml`: low/medium risk run `quick` mode, no human-in-the-loop).
- All nine acceptance criteria in `api-e2e.spec.md` must be satisfied: real out-of-process server
  startup (BEH-1 precondition), fresh-seed visibility (BEH-1), full Incident lifecycle including
  the unguarded patch (BEH-2), the `account_id`+`opened_after` analytics-parity filter (BEH-3),
  ownerless Escalations and business-hours-measured SLA records reading without error (BEH-4),
  the user/assignment-group directory (BEH-5), documented 404/422 error responses (BEH-6), a
  valid `GET /openapi.json` document listing every route (BEH-7), all quality gates passing, and
  no constitutional violations.
- Task 7 additionally closes review note SA-1: all three seeded discrepancies — including the
  resolved-Incident/open-`first_response`-breach discrepancy that had no Behavior asserting it at
  review time — are now guarded by a real-HTTP presence test.
