---
charter: itsm-api
status: validated
risk_level: low
milestone: mvp
revision: 2
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
source-manifest:
  sha: "ce7c750"
  files:
    - app/main.py
    - app/models.py
    - app/routers/directory.py
    - pytest.ini
    - tests/test_directory.py
  computed-at: "2026-09-07T18:49:50.859Z"
---

# Live Spec: User and assignment group directory

<!-- Live Spec within the itsm-api charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/itsm-api/charter.md -->

## Behavioral Contract

### Preconditions

- No authentication is required to reach either endpoint (per charter: no real auth in scope).
  SysUser is a directory record, never an account — it carries no password, token, session, or
  permissions semantics.
- This spec is read-only: `POST`/`PATCH`/`DELETE` on `/users` or `/assignment_groups` are out of
  scope this milestone (see charter's Deferred Capabilities) — the support-team roster is fixed
  course fixture data.
- `Incident.assigned_to` and `Incident.assignment_group` remain free-text fields, not enforced
  foreign keys to `SysUser`/`AssignmentGroup` (per charter's Domain Model, mirroring `mock-jira`'s
  `Issue.assignee` pattern) — this spec's directory is a reference for consumers, not a
  referential-integrity constraint enforced elsewhere in this API.
- **Field-level schema** (PRD.md's own "Data model" section gives no field table for these two
  entities, unlike `incident`/`work_note`/`escalation`/`task_sla` — this spec is the authority):
  - `SysUser`: `name` (text, PK — a person's full name, e.g. `Rui Bastos`; unique, never reused),
    `role` (text — one of `Support Manager`, `Support Engineer`, `Solution Consultant`),
    `assignment_group` (text, nullable, FK-by-name to `AssignmentGroup.name` — nullable because
    the Support Manager role sits outside the three tiers).
  - `AssignmentGroup`: `name` (text, PK — one of `Support Tier 1`, `Support Tier 2`,
    `Solution Consultants`).
- **Reconciling the canon's partial naming.** `course-shared/canon/company.md` names only three
  of the nine support-team members individually (Rui Bastos, Priya Nair, Joao Pinto); the
  remaining six (five more Support Engineers, one more Solution Consultant) are described there
  only as an aggregate headcount, with no individual names given. Per the same authoring-time
  reconciliation principle `fixture-seeding.spec.md` already applies to Principle 1 (external
  sources are vendored into this repo once, at authoring time, never read live), the seed
  author invents plausible names for these six at seeding-authoring time and adds them to this
  repo's own vendored copy of the roster — never edits `course-shared/canon/company.md` itself.
  Invented names must not collide with any name already reserved in
  `course-shared/canon/identifiers.md` or `company.md` (constitution Principle 3).

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** a `GET /users` request is sent, **then** the API responds `200` with a
  paginated page of every SysUser record (name and assignment-group membership), covering the
  full seeded support-team directory (the nine-person support team plus the other named
  individuals from the canon that appear elsewhere in this fixture set, per PRD.md's "Seed data"
  section — roughly a dozen rows total).
- **BEH-2** — **When** a `GET /assignment_groups` request is sent, **then** the API responds
  `200` with exactly three AssignmentGroup records: `Support Tier 1`, `Support Tier 2`, and
  `Solution Consultants` — no more, no fewer.
- **BEH-3** — **When** any SysUser record is returned, **then** its group membership (if any)
  names one of the three AssignmentGroups from BEH-2 — never an invented or unlisted group name.
- **BEH-4** — **When** a `GET /users` or `GET /assignment_groups` request is sent, **then** the
  response is a paginated page (per the charter's pagination-on-every-list-endpoint quality
  attribute) even though the fixed, small directory size means the default page size typically
  returns every row in a single page.

### Postconditions

- `GET /users` and `GET /assignment_groups` never mutate any Incident, WorkNote, Escalation, or
  TaskSla row — both are pure reads.
- The directory's contents are stable across repeated calls unless the underlying data is
  reseeded (see `fixture-seeding` spec).

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Invalid pagination parameter (non-integer page/page size) | `422 Unprocessable Entity`, JSON body naming the invalid parameter | `VALIDATION_ERROR` |

## System Constitution Reference

- **Principle 3:** "Identifiers reconcile with the shared canon... user/group names must be
  consistent with `course-shared/canon/identifiers.md`." — Applies directly: every SysUser name
  and every AssignmentGroup name this spec serves is drawn from `course-shared/canon/company.md`.
- **Principle 4:** "The HTTP contract is the boundary." — Applies because this spec defines the
  directory slice of that contract, the reference other tracks use to validate `assigned_to`/
  `assignment_group` values they see on Incidents.
- **Principle 2:** "Fixture-backed, offline only." — Applies because the entire directory is
  local, seeded data; this spec makes no live call to any identity provider.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Define the SysUser and AssignmentGroup tables | SQLite tables per PRD.md's `sys_user`/`assignment_group` schema | small |
| Implement `GET /users` | Query all SysUsers, paginated | small |
| Implement `GET /assignment_groups` | Query all three AssignmentGroups, paginated | small |

## Acceptance Criteria

- [ ] `GET /users` returns the full seeded directory, paginated (BEH-1)
- [ ] `GET /assignment_groups` returns exactly the three named groups (BEH-2)
- [ ] Every SysUser's group membership names one of the three AssignmentGroups (BEH-3)
- [ ] Both endpoints return a paginated page shape per the charter's quality attribute (BEH-4)
- [ ] No create/update/delete endpoint exists for either entity this milestone
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
