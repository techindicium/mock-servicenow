---
charter: itsm-api
status: review-passed
risk_level: medium
milestone: mvp
revision: 1
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
---

# Live Spec: Fixture seed data

<!-- Live Spec within the itsm-api charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/itsm-api/charter.md -->

## Behavioral Contract

### Preconditions

- The `incident-lifecycle`, `work-notes`, `escalations`, `sla-records`, and `user-directory`
  specs' schemas exist — seeding writes through the same six tables those specs define.
- The seed command is a documented, explicitly-invoked step (per PRD.md: "a documented command
  that runs from a clean container"), distinct from any implicit seed-on-startup behavior — it
  can be run once at container build/first-start and re-run any number of times thereafter.
- Reconciliation with `../course-shared/canon` (`identifiers.md`, `company.md`) and vendoring of
  the `../portwell-assist` CSVs and `../portwell-knowledge` escalation sheets happens once, at
  implementation/authoring time, never at seed-command runtime. The source rows the seed command
  reads live as static fixture files committed inside this repository — a one-time, authoring-time
  copy of the sources PRD.md's "Seed data" section names. The running seed command never opens a
  file outside this repository. This is non-negotiable: a runtime read of `../portwell-assist`,
  `../portwell-knowledge`, or `../course-shared/*` would be an inbound dependency on another repo
  or on `course-shared`, which constitution Non-Negotiable Principle 1 forbids outright.
- Recording the three seeded discrepancies in `../course-shared/heldout/seeded-defects.md` (per
  PRD.md: "Record all three... when seeding lands") is a one-time documentation action performed
  by whoever implements this spec, coincident with landing the seed command — not a write the
  running seed command performs at every invocation. A runtime write across the repo boundary on
  every seed run would itself be exactly the kind of inbound dependency Principle 1 forbids; see
  the Actionable Task Map for this as an explicit implementation task rather than a Behavior.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** the seed command is run against an empty database (no rows in any of the
  six tables), **then** it loads exactly 1,307 Incidents and 2,614 WorkNotes from the vendored
  copies of `tickets.csv`/`interactions.csv`, exactly 5 Escalations from the vendored
  `portwell-knowledge` escalation sheets, one or two TaskSla records per Incident derived from
  the Incident's account tier commitment and its WorkNote timestamps, and roughly a dozen
  SysUser/AssignmentGroup rows from the vendored `company.md` data — all in a way that leaves
  every table fully populated and immediately queryable once the command completes.
- **BEH-2** — **When** the seed command is run again against an already-seeded database, **then**
  it is idempotent: no table gains a duplicate row, and every table's row count and content after
  the second run is identical to after the first run. This holds for any number of repeated runs,
  not just a second one.
- **BEH-3** — **When** the seed command loads the ten narrative tickets named in PRD.md (the
  tickets `portwell-assist`'s own tests key on), **then** each keeps its exact `number` and
  content byte-identical to the source CSV, across every run of the seed command, forever — this
  identifier stability is never affected by BEH-2's idempotency mechanism reordering or
  regenerating rows.
- **BEH-4** — **When** the seed command derives TaskSla records, **then** the derivation is
  deterministic: the same Incident and WorkNote source data always produces the same
  `target_minutes`, `actual_minutes`, `has_breached`, and `business_time_only` values, run after
  run, so re-seeding never silently changes a previously-reported SLA figure.
- **BEH-5** — **When** the seed command completes (on the first run or any subsequent idempotent
  run), **then** the SLA business-hours/wall-clock discrepancy (resolution-SLA
  `actual_minutes` measured in business hours while the analytics warehouse computes wall-clock
  elapsed time for the same interval), the two ownerless Escalations (`owner: null`), and the
  incidents `resolved` or `closed` with their `first_response` TaskSla still `has_breached: true`
  are all present, exactly as seeded — none of the three is corrected, filtered, or normalized by
  the seed command itself.

### Postconditions

- After any successful seed run, `GET /incidents` returns exactly 1,307 Incidents,
  `GET /incidents/{number}/work_notes` across all incidents totals exactly 2,614 WorkNotes,
  `GET /escalations` returns exactly 5 Escalations (two with `owner: null`), `GET /sla` returns
  one or two records per Incident, and `GET /users`/`GET /assignment_groups` return the full
  seeded directory.
- The ten narrative tickets' `number` values are stable identifiers `portwell-assist` can key on
  indefinitely — they are never renumbered by any seed run, past or future.
- No seed run ever reaches a file path outside this repository, and no seed run ever reaches a
  real network endpoint.

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| A vendored source row fails validation (malformed CSV row, unparseable timestamp, unknown enum value) | Seed command aborts with a clear error naming the offending row and file | `SEED_DATA_INVALID` |
| The database file path is not writable | Seed command aborts with a clear error naming the path | `SEED_DB_NOT_WRITABLE` |
| The seed command is invoked with a database already mid-migration or in an inconsistent partial state | Seed command aborts rather than guessing; names the inconsistency | `SEED_STATE_INCONSISTENT` |

## System Constitution Reference

- **Principle 1:** "No inbound dependencies. This repo never depends on `course-shared`, another
  `mock-*` repo, or any track repo." — Applies directly to the Preconditions: reconciliation and
  vendoring of every external source happen once, at authoring time, and the seed command itself
  never crosses the repo boundary at runtime.
- **Principle 2:** "Fixture-backed, offline only." — Applies directly: this spec is the mechanism
  that makes every other endpoint's data fixture-backed.
- **Principle 3:** "Identifiers reconcile with the shared canon... the ten narrative tickets keep
  their exact identifiers." — Applies directly to BEH-3.
- **Principle 6:** "Seeded discrepancies are load-bearing, not bugs... must persist across
  reseeds and must never be corrected." — Applies directly to BEH-4 and BEH-5: this spec exists
  specifically to make the three discrepancies reproducible, not to eliminate them.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Vendor the source fixtures into this repo | One-time copy of `tickets.csv`/`interactions.csv`, the `portwell-knowledge` escalation sheets, and the relevant `company.md` rows into this repo's own fixture directory, reconciled against canon at authoring time | medium |
| Write the seed command | Loads all six tables from the vendored fixtures in a single transaction, empty-database detection, idempotent re-run behavior | large |
| Derive TaskSla records | Deterministic derivation from account tier commitment + WorkNote timestamps, preserving `business_time_only` and the open-breach discrepancy | medium |
| Idempotency test | Run the seed command twice (and more) against the same database file; assert identical row counts and content after each run | small |
| Discrepancy-presence test | Assert all three seeded discrepancies are present and reproducible after every seed run | small |
| Record the discrepancies in `course-shared/heldout/seeded-defects.md` | One-time documentation action performed when this spec's implementation lands, per PRD.md — not a runtime write by the seed command | small |

## Acceptance Criteria

- [ ] A fresh-database seed run loads all six tables with the exact documented row counts, no placeholder data (BEH-1)
- [ ] Re-running the seed command against an already-seeded database is idempotent — no duplicate rows, identical content (BEH-2)
- [ ] The ten narrative tickets keep their exact identifiers and content across every reseed (BEH-3)
- [ ] TaskSla derivation is deterministic across repeated seed runs (BEH-4)
- [ ] All three seeded discrepancies are present and reproducible after every seed run (BEH-5)
- [ ] No seed run reads or writes any path outside this repository at runtime
- [ ] The three seeded discrepancies are recorded in `course-shared/heldout/seeded-defects.md` as a one-time delivery action when this spec is implemented
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
