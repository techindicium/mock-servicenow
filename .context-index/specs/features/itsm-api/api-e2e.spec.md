---
charter: itsm-api
status: validated
risk_level: low
milestone: v1.1
revision: 1
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
source-manifest:
  sha: "8c7838c"
  files:
    - .context-index/governance/gates.yaml
    - tests/test_gates_config.py
    - tests/test_pytest_config.py
    - tests_e2e/__init__.py
    - tests_e2e/conftest.py
    - tests_e2e/servers.py
    - tests_e2e/test_analytics_filter_e2e.py
    - tests_e2e/test_directory_e2e.py
    - tests_e2e/test_error_paths_e2e.py
    - tests_e2e/test_escalations_e2e.py
    - tests_e2e/test_incident_crud_e2e.py
    - tests_e2e/test_openapi_e2e.py
    - tests_e2e/test_seeded_discrepancies_e2e.py
    - tests_e2e/test_server_fixture.py
    - tests_e2e/test_sla_e2e.py
    - tests_e2e/test_work_notes_e2e.py
  computed-at: "2026-09-07T23:39:07.228Z"
---

# Live Spec: End-to-end API test suite (real HTTP)

<!-- Live Spec within the itsm-api charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/itsm-api/charter.md -->

## Behavioral Contract

### Preconditions

- The full Incident/WorkNote/Escalation/TaskSla/directory surface (`incident-lifecycle`,
  `work-notes`, `escalations`, `sla-records`, `user-directory`, `fixture-seeding` specs) is
  implemented.
- These tests start the real application as its own OS process — bound to an ephemeral local
  port, with its database pointed at a fresh temporary file (freshly seeded via the documented
  seed command) per test session — and poll `GET /` (the health/version route) until it responds,
  before any test runs. They never import the application's Python objects into the test process
  and never use FastAPI's in-process `TestClient` (an in-process ASGI transport). This is the one
  thing that distinguishes this spec from the module's existing unit/integration tests: every
  request in this suite travels over a real TCP socket, exactly as `portwell-portal`,
  `portwell-analytics`, or `portwell-knowledge` would connect.
- A real HTTP client (e.g. `httpx.Client(base_url=...)`) issues every request in this suite.
- The server process is torn down after the test session, whether it passed or failed.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** the real server process starts against a freshly seeded database and a
  real `GET /incidents` request is sent, **then** it returns the full seeded Incident set over
  the same live HTTP connection to the same process — proving seed-then-serve works end to end,
  not just under test-harness conditions.
- **BEH-2** — **When** a full Incident lifecycle (create → list/get with filters → patch
  state/priority/assigned_to/assignment_group → list/add work notes) is driven as a sequence of
  real HTTP requests against the live server, **then** every step succeeds and matches the
  documented contract, end to end, including the unguarded nature of the patch step (no
  permission/business-rule guard rejects any valid state transition).
- **BEH-3** — **When** a real `GET /incidents?account_id=ACCOUNT-1001&opened_after=2026-08-01`
  request is sent to the live server, **then** it returns exactly the set of Incidents that
  independently filtering the seeded fixture data the same way (by `account_id` and `opened_at`)
  produces — the same set the analytics warehouse would return for that filter, per PRD.md's
  Acceptance section.
- **BEH-4** — **When** real HTTP requests exercise the Escalation and TaskSla endpoints,
  **then** they correctly read the seeded ownerless Escalations (`owner: null`) and the seeded
  `business_time_only: true` resolution-SLA records without any endpoint treating either as an
  error.
- **BEH-5** — **When** real HTTP requests exercise `GET /users` and `GET /assignment_groups`,
  **then** they return the full seeded support-team directory and exactly the three named
  assignment groups.
- **BEH-6** — **When** a request that should fail (unknown incident/escalation number, invalid
  `state`/`priority`/`note_type`/`sla_definition` value) is sent as a real HTTP request, **then**
  the live server returns the documented status code and error body — not just a mocked or
  in-process equivalent.
- **BEH-7** — **When** a real `GET /openapi.json` request is sent to the live server, **then** it
  returns a valid OpenAPI document listing every implemented route from PRD.md's API surface.

### Postconditions

- No test in this suite ever calls into the application's Python objects directly — every
  assertion is made against an HTTP client response coming back over a real socket.
- The temporary database file and server process used by this suite are cleaned up after the
  session; a second run starts from a clean, freshly seeded slate.
- No request in this suite ever reaches a real network endpoint outside the locally started
  server process.

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Real server process fails to become healthy within the startup timeout | Test setup fails loudly, naming the timeout and the last-seen process output — never a silent hang | `E2E_SERVER_START_TIMEOUT` |
| A real HTTP request targets an unknown Incident/Escalation number | `404`, matching the documented `INCIDENT_NOT_FOUND`/`ESCALATION_NOT_FOUND` body | (inherited from `incident-lifecycle`/`escalations`) |
| A real HTTP request submits an invalid `state`/`priority`/`note_type`/`sla_definition` value | `422`, matching `VALIDATION_ERROR` | (inherited) |
| The freshly seeded server does not reflect the three seeded discrepancies | Test fails, naming which discrepancy is missing — this suite is a guard against a future seed change accidentally removing one | `E2E_DISCREPANCY_MISSING` |

## System Constitution Reference

- **Principle 4:** "The HTTP contract is the boundary." — Applies directly: this suite is the one
  place in the repo that actually exercises that boundary as a real network client would, rather
  than through an in-process shortcut.
- **Principle 2:** "Fixture-backed, offline only." — Applies because the real server this suite
  starts is bound to localhost only, never a real external network.
- **Principle 6:** "Seeded discrepancies are load-bearing, not bugs... must persist across
  reseeds." — Applies directly to BEH-4 and the `E2E_DISCREPANCY_MISSING` error case: this suite
  is the strongest guard against an accidental future change silently removing a discrepancy.
- **Principle 7:** "Breaking API changes are coordinated, not silent." — Applies because this
  suite is the strongest guard against an accidental contract break: it fails if the real,
  running server's actual wire behavior ever diverges from what the other specs say.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Real-server-process fixture | A test fixture that launches the application as a subprocess on an ephemeral port with a temp database path, runs the seed command, polls until healthy, yields the base URL, and tears down afterward | medium |
| Incident lifecycle e2e tests | HTTP-driven tests for BEH-1 and BEH-2 | medium |
| Analytics-parity filter e2e test | HTTP-driven test for BEH-3, cross-checked against independently filtered fixture data | small |
| Escalation/SLA e2e tests | HTTP-driven tests for BEH-4, asserting null/true fields never error | small |
| Directory e2e tests | HTTP-driven tests for BEH-5 | small |
| Error-path e2e tests | HTTP-driven tests for BEH-6 | small |
| OpenAPI e2e test | HTTP-driven test for BEH-7 | small |
| Discrepancy-presence e2e test | HTTP-driven test asserting all three seeded discrepancies are visible over real HTTP after a fresh seed | small |

## Acceptance Criteria

- [ ] The real server starts as its own process (never imported in-process) and becomes healthy before tests run (BEH-1 precondition)
- [ ] Fresh-seed data is visible over real HTTP on server start (BEH-1)
- [ ] Full Incident lifecycle, including the unguarded patch step, succeeds over a sequence of real HTTP requests (BEH-2)
- [ ] `GET /incidents?account_id=ACCOUNT-1001&opened_after=2026-08-01` matches the independently filtered fixture set (BEH-3)
- [ ] Ownerless escalations and business-hours-measured SLA records read correctly with no error (BEH-4)
- [ ] User and assignment-group directory reads correctly over real HTTP (BEH-5)
- [ ] Documented error responses (404/422) are returned correctly over real HTTP (BEH-6)
- [ ] `GET /openapi.json` over real HTTP returns a valid document listing every route (BEH-7)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
