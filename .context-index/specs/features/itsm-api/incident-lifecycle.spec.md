---
charter: itsm-api
status: implemented
risk_level: medium
milestone: mvp
revision: 1
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
source-manifest:
  sha: "a33fa68"
  files:
    - app/db.py
    - app/errors.py
    - app/main.py
    - app/models.py
    - app/pagination.py
    - app/routers/incidents.py
    - requirements.txt
    - tests/conftest.py
    - tests/test_db.py
    - tests/test_incidents.py
  computed-at: "2026-09-07T18:26:07.486Z"
---

# Live Spec: Incident lifecycle CRUD

<!-- Live Spec within the itsm-api charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/itsm-api/charter.md -->

## Behavioral Contract

### Preconditions

- The API process is running and its SQLite database is available.
- This spec applies no permission check and no business-rule/state-transition guard to
  `PATCH /incidents/{number}` — per constitution Non-Negotiable Principle 5, this HTTP layer
  never adds a write guard the MCP layer intentionally omits. Any actor may move any Incident to
  any of the five fixed `state` values, set any `priority` 1-4, and set `assigned_to`/
  `assignment_group` to any value, including resolving an Incident that has an open SLA breach
  or an unanswered customer. "Unguarded" means no permission/business-rule check — it does not
  mean no structural validation: `state` and `priority` still must be one of the fixed, valid
  values (see Behaviors and Error Cases), matching the Domain Model invariant that the API
  rejects a `state` or `priority` value outside the fixed set.
- Incidents are seeded before this spec's `POST`/`PATCH` behaviors are exercised in practice (see
  `fixture-seeding` spec), but none of the behaviors below depend on any specific seeded row.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** a `GET /incidents` request is sent with no query parameters, **then** the
  API responds `200` with a paginated page of Incidents (page metadata plus items), covering the
  full unfiltered set across as many pages as needed — never a single unpaginated response of all
  1,307+ rows.
- **BEH-2** — **When** a `GET /incidents` request is sent with any combination of `account_id`,
  `state`, `category`, `opened_after`, `opened_before`, and `escalated` query parameters, **then**
  the API responds `200` with exactly the Incidents matching the intersection of all given
  filters (`opened_after`/`opened_before` bound `opened_at` inclusive/exclusive per ISO-timestamp
  comparison), still paginated.
- **BEH-3** — **When** a `GET /incidents/{number}` request is sent for a `number` that exists,
  **then** the API responds `200` with that Incident's full representation.
- **BEH-4** — **When** a `GET /incidents/{number}` request is sent for a `number` that does not
  exist, **then** the API responds `404` naming the missing number.
- **BEH-5** — **When** a `POST /incidents` request is sent with all required fields
  (`account_id`, `category`, `short_description`, `description`, `state`, `priority`), **then**
  the API creates the Incident with a server-assigned `number` in the `TICKET-NNNNNN` scheme,
  guaranteed not to collide with any seeded or previously created number, and responds `201` with
  the full representation. `escalated` defaults to `false` and `resolved_at`/`assigned_to` default
  to null when omitted.
- **BEH-6** — **When** a `POST /incidents` request is missing a required field, **then** the API
  responds `422` naming the missing field, and creates no Incident.
- **BEH-7** — **When** a `POST /incidents` or `PATCH /incidents/{number}` request sets `state` to
  a value outside `new`, `in_progress`, `on_hold`, `resolved`, `closed`, or sets `priority` to a
  value outside the integer range 1-4, **then** the API responds `422` naming the invalid field
  and its allowed values, and persists no change.
- **BEH-8** — **When** a `PATCH /incidents/{number}` request is sent with one or more of `state`,
  `priority`, `assigned_to`, `assignment_group` for a `number` that exists, **then** the API
  updates exactly those fields and responds `200` with the full updated representation — with no
  check on whether the transition is sensible (e.g. `new` directly to `closed`), whether
  `assigned_to` is a known user, or whether an open SLA breach or unanswered customer exists (see
  Preconditions). `number`, `account_id`, and `opened_at` are not mutable fields and are silently
  ignored if present in the request body.
- **BEH-9** — **When** a `PATCH /incidents/{number}` request is sent for a `number` that does not
  exist, **then** the API responds `404` naming the missing number, and persists no change.

### Postconditions

- Every Incident created via `POST /incidents` is immediately retrievable via `GET /incidents`
  (with matching filters), `GET /incidents?account_id=...`, and `GET /incidents/{number}` — no
  eventual consistency window.
- An Incident's `number` never changes once assigned, whether seeded or created via `POST`, and
  is never reused.
- Resolving an Incident (`state: resolved` or `closed`) never touches its `task_sla` records —
  those are a separate entity this spec does not write to (see `sla-records` spec).

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Missing required field on create | `422 Unprocessable Entity`, JSON body naming the missing field | `VALIDATION_ERROR` |
| Invalid `state` or `priority` value on create/patch | `422 Unprocessable Entity`, JSON body naming the invalid field and its allowed values | `VALIDATION_ERROR` |
| Unknown `number` on get/patch | `404 Not Found`, JSON body naming the missing number | `INCIDENT_NOT_FOUND` |
| Malformed JSON request body | `400 Bad Request` | `MALFORMED_JSON` |
| Invalid `opened_after`/`opened_before` value (not a parseable ISO timestamp) | `422 Unprocessable Entity`, JSON body naming the invalid parameter | `VALIDATION_ERROR` |

## System Constitution Reference

- **Principle 5:** "The MCP tools stay unguarded... Building safety around them is the exercise;
  do not add permission checks here even if a consuming track's own wrapper is buggy." — Applies
  directly: `PATCH /incidents/{number}` is the HTTP endpoint the MCP `update_incident` tool
  wraps, and this spec's BEH-8 is the explicit statement that this layer adds no guard either.
- **Principle 4:** "The HTTP contract is the boundary. Consuming tracks integrate through the
  documented API only." — Applies because this spec defines the single most consumer-visible
  slice of that contract: the Incident CRUD surface every consuming track reads and writes.
- **Principle 3:** "Identifiers reconcile with the shared canon... the ten narrative tickets keep
  their exact identifiers." — Applies because `GET`/`PATCH` by `number` never renumbers or
  reassigns a seeded Incident's identifier.
- **Principle 6:** "Seeded discrepancies are load-bearing, not bugs." — Applies because BEH-8's
  lack of a resolve-with-open-breach guard is exactly the mechanism that lets seeded
  discrepancy #3 (resolved incidents with an open `first_response` breach) exist and persist.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Define the Incident table | SQLite table per PRD.md's `incident` schema, with `number` as PK | medium |
| Implement `GET /incidents` with filters and pagination | Query builder for `account_id`/`state`/`category`/`opened_after`/`opened_before`/`escalated`, page params | medium |
| Implement `GET /incidents/{number}` | Query by number, 404 if missing | small |
| Implement `POST /incidents` | Validation, `number` generation avoiding collisions, insert, default fields | medium |
| Implement `PATCH /incidents/{number}` | Partial update of `state`/`priority`/`assigned_to`/`assignment_group`, structural enum validation only, no permission/business-rule guard | medium |

## Acceptance Criteria

- [ ] `GET /incidents` returns a paginated, unfiltered page by default (BEH-1)
- [ ] `GET /incidents` narrows results to the intersection of any combination of its six filters (BEH-2)
- [ ] `GET /incidents/{number}` returns 200 for an existing number (BEH-3)
- [ ] `GET /incidents/{number}` returns 404 for an unknown number (BEH-4)
- [ ] `POST /incidents` creates an Incident with a server-assigned, non-colliding number and returns 201 (BEH-5)
- [ ] `POST /incidents` with a missing required field returns 422 (BEH-6)
- [ ] Invalid `state`/`priority` values are rejected with 422 on both create and patch (BEH-7)
- [ ] `PATCH /incidents/{number}` updates state/priority/assigned_to/assignment_group with no permission or business-rule guard (BEH-8)
- [ ] `PATCH /incidents/{number}` returns 404 for an unknown number (BEH-9)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
