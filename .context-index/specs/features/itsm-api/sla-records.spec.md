---
charter: itsm-api
status: validated
risk_level: low
milestone: mvp
revision: 1
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
source-manifest:
  sha: "a5a3b94"
  files:
    - app/db.py
    - app/main.py
    - app/models.py
    - app/routers/sla.py
    - tests/conftest.py
    - tests/test_sla.py
  computed-at: "2026-09-09T11:24:00.266Z"
---

# Live Spec: Task SLA record listing

<!-- Live Spec within the itsm-api charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/itsm-api/charter.md -->

## Behavioral Contract

### Preconditions

- The `incident-lifecycle` spec's Incident table exists — every TaskSla record's
  `incident_number` references a seeded or created Incident.
- `GET /sla` is the only endpoint this spec defines. TaskSla records are derived at seed time
  (see `fixture-seeding` spec) from tier commitments and work-note timestamps; there is no
  `POST`/`PATCH /sla` in this API surface this milestone — TaskSla is read-only over HTTP.
- Every TaskSla record carries `business_time_only`, a stored fact describing how its
  `actual_minutes` value was measured for that `sla_definition`: `true` when `actual_minutes` was
  computed against business hours only, `false` when it was computed against elapsed wall-clock
  time. This spec's endpoint reports the field exactly as stored; it performs no unit conversion
  and asserts no relationship between a `business_time_only: true` record's `actual_minutes` and
  what a wall-clock computation over the same interval would produce.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** a `GET /sla` request is sent with no query parameters, **then** the API
  responds `200` with a paginated page of every TaskSla record.
- **BEH-2** — **When** a `GET /sla?incident_number=...` request is sent, **then** the API
  responds `200` with exactly the TaskSla records for that Incident (one or two, per
  `sla_definition`), or an empty array if the Incident has none.
- **BEH-3** — **When** a `GET /sla?breached=true` or `GET /sla?breached=false` request is sent,
  **then** the API responds `200` with exactly the TaskSla records whose `has_breached` matches.
- **BEH-4** — **When** a `GET /sla?sla_definition=first_response` or
  `GET /sla?sla_definition=resolution` request is sent, **then** the API responds `200` with
  exactly the TaskSla records matching that `sla_definition`.
- **BEH-5** — **When** a `GET /sla` request combines `incident_number`, `breached`, and/or
  `sla_definition`, **then** the API responds `200` with exactly the records matching the
  intersection of all given filters.
- **BEH-6** — **When** a `GET /sla` request is sent for a filter combination matching no records
  (e.g. an `incident_number` with no TaskSla rows, or a valid `sla_definition` value that happens
  to match nothing given the other filters), **then** the API responds `200` with an empty array
  — never `404`, because `incident_number` here is a filter on a list endpoint, not a path
  resource lookup.
- **BEH-7** — **When** any TaskSla record is returned by `GET /sla`, **then** its
  `business_time_only` field is present and boolean-valued in every response, `true` for every
  `resolution`-definition record in the fixture set.

### Postconditions

- `GET /sla` never mutates any Incident, WorkNote, or Escalation row — it is a pure read.
- The set of TaskSla records returned for a given `incident_number` is stable across repeated
  calls unless the underlying data is reseeded (see `fixture-seeding` spec).

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Invalid `sla_definition` value (not `first_response`/`resolution`) | `422 Unprocessable Entity`, JSON body naming the invalid value and its allowed values | `VALIDATION_ERROR` |
| Invalid `breached` value (not a parseable boolean) | `422 Unprocessable Entity`, JSON body naming the invalid parameter | `VALIDATION_ERROR` |
| Unknown `incident_number` filter value | `200 OK` with an empty array (see BEH-6) — not an error | — |

## System Constitution Reference

- **Principle 4:** "The HTTP contract is the boundary." — Applies because `GET /sla` is the
  mechanism that gives the reporting pack's SLA-attainment figure a checkable source, per the
  charter's Business Intent for this entity ("the reason it is worth building").
- **Principle 6:** "Seeded discrepancies are load-bearing, not bugs... the SLA business-hours/
  wall-clock disagreement... must persist across reseeds and must never be corrected." — Applies
  directly: BEH-7 and the Preconditions note describe `business_time_only` factually, as a
  measurement-method field this endpoint reports without correction or reconciliation against
  any other figure.
- **Principle 2:** "Fixture-backed, offline only." — Applies because every TaskSla value served
  here comes from local, seeded data; nothing in this spec computes a fresh figure at read time.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Define the TaskSla table | SQLite table per PRD.md's `task_sla` schema, with `incident_number` FK | small |
| Implement `GET /sla` with filters and pagination | Query builder for `incident_number`/`breached`/`sla_definition`, page params | small |

## Acceptance Criteria

- [ ] `GET /sla` returns a paginated, unfiltered page by default (BEH-1)
- [ ] `GET /sla?incident_number=...` filters correctly, empty array when none exist (BEH-2)
- [ ] `GET /sla?breached=...` filters correctly (BEH-3)
- [ ] `GET /sla?sla_definition=...` filters correctly (BEH-4)
- [ ] Combined filters narrow to their intersection (BEH-5)
- [ ] A filter combination matching nothing returns 200 with an empty array, never 404 (BEH-6)
- [ ] Every record's `business_time_only` field is present and correct (BEH-7)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
