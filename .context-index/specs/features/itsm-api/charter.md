---
status: approved
kind: feature
revision: 20
updated: 2026-09-09
---

# Feature Charter: itsm-api

<!-- Feature Charter for the itsm-api module.
     This defines WHAT the module does and its boundaries, not HOW it is built.
     Live Specs within this charter define specific behavioral contracts. -->

## Business Intent

itsm-api provides a ServiceNow-shaped ITSM domain (incidents, work notes, escalations, SLA
records) backed by a local SQLite database, exposed over an HTTP API. It is the system of record
for Portwell's support desk, and exists so the adev-course tracks that need a realistic upstream
ITSM system — `portwell-portal` (SDLC), `portwell-analytics` (DDLC), and `portwell-knowledge`
(KDLC) — have something concrete and offline to integrate against, without any real ServiceNow
instance involved. This is the core module of `mock-servicenow`: `mcp-server` is a pure client of
this API, never the other way around.

Today those three tracks read ticket data from a committed SQLite file and a CSV extract — fine
for a Module 1 lifecycle exercise, useless for Module 2, where the subject is tool mediation. An
HTTP API that can fail interestingly, half-succeed, and take an irreversible write (closing a
ticket) is the point of building this at all.

## Scope and Boundaries

### In Scope

- Incident entity: the support ticket, with category, state, priority, assignment, and
  escalation flag, per PRD.md's `incident` table.
- Work note entity: one row per message or action on an incident (comment, work_note,
  state_change, proposal_sent), authored by `customer`, an agent name, or `assist`.
- Escalation entity: a small, mostly-open set of escalation records, some ownerless by design.
- Task SLA entity: first-class SLA attainment records per incident (`first_response`,
  `resolution`), the source figure the reporting packs must ultimately be checkable against.
- Sys user and assignment group entities: the support team directory, per
  `course-shared/canon/company.md`.
- Full CRUD-shaped HTTP endpoints exactly as PRD.md's "API surface" section specifies: incident
  list/get/create/update, work-note list/add, escalation list/get/create/update, SLA list, user
  list, assignment-group list. Pagination on every list endpoint.
- SQLite persistence, a single local file, created fresh on first run.
- A documented, idempotent seed command loading all six tables from the sources PRD.md's "Seed
  data" section names (`portwell-portal` ticket/interaction CSVs, `portwell-knowledge` escalation
  sheets, tier-commitment-derived SLA records, `course-shared/canon/company.md`), preserving the
  ten narrative tickets' exact identifiers and content.
- The three seeded discrepancies from PRD.md's "Seeded discrepancies" section (SLA
  business-hours-vs-wall-clock disagreement, two ownerless escalations, incidents resolved with
  an open SLA breach), present and reproducible from the first seed, recorded only in
  `course-shared/heldout/seeded-defects.md`.
- An OpenAPI-documented HTTP contract (auto-generated from the implementation, not
  hand-maintained).

### Out of Scope

- Authentication/authorization/credentials/sessions — no login, no token, no session, no
  permissions semantics anywhere in this API, per PRD.md's non-goals.
- The ServiceNow scripting engine, workflows, the Now UI, CMDB, change management, catalogue
  items, approvals as a subsystem, notifications — all explicitly out of scope per PRD.md.
- Post-incident write-ups (`docs/incidents/` in each consuming repo) — those are documents a
  person wrote after the fact; the incident *records* live here, the *reviews* do not.
- "Fixing," documenting inline, or otherwise surfacing the three seeded discrepancies anywhere a
  participant can read — see Non-Negotiable Principle 6 in this repo's constitution.
- A ServiceNow-style `/api/now/table/...` path scheme — this API follows the existing mocks'
  plain path style instead, per PRD.md's "API surface" note.

### Dependencies

| Dependency | Type | Description |
|-----------|------|-------------|
| `../course-shared/canon/identifiers.md` and `company.md` | shared reference (read-only) | Seed fixture identifiers (accounts, users, groups) must reconcile with the canon. Not a runtime/code dependency. |
| `../portwell-portal/data/seed/history/{tickets.csv,interactions.csv}` | seed source (read-only, seed-time only) | Source rows for `incident`/`work_note`. Read once by the seed command; never a runtime dependency. |
| `../portwell-knowledge` escalation pack sheets | seed source (read-only, seed-time only) | Source rows for `escalation`. |
| `../course-shared/heldout/seeded-defects.md` | shared reference (write, seed-time only) | Where the three seeded discrepancies are recorded once seeding lands — not readable by participants during the course. |

## Domain Model

### Entities

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| Incident | The support ticket | `number` (PK, e.g. `TICKET-004417`), `account_id`, `category`, `short_description`, `description`, `state`, `priority`, `opened_at`, `resolved_at`, `assigned_to`, `assignment_group`, `escalated` |
| WorkNote | One message or action on an incident | `sys_id` (PK, e.g. `INTERACTION-0100001`), `incident_number` (FK), `created_at`, `created_by`, `note_type`, `body` |
| Escalation | An open (or closed) escalation, sometimes ownerless | `number` (PK, e.g. `ESCALATION-0412`), `incident_number` (FK, nullable), `account_id`, `summary`, `opened_at`, `closed_at`, `owner` (nullable) |
| TaskSla | An SLA attainment record for an incident | `sys_id` (PK), `incident_number` (FK), `sla_definition` (`first_response`\|`resolution`), `target_minutes`, `actual_minutes` (nullable), `has_breached`, `business_time_only` |
| SysUser | A support-team directory record | `name`, group membership |
| AssignmentGroup | A support team grouping | `name` (`Support Tier 1`, `Support Tier 2`, `Solution Consultants`) |

### Relationships

- Every WorkNote belongs to exactly one Incident (`WorkNote.incident_number` → `Incident.number`).
- Every TaskSla belongs to exactly one Incident (`TaskSla.incident_number` → `Incident.number`);
  an Incident may have one or two TaskSla records (`first_response`, `resolution`).
- An Escalation may reference zero or one Incident (`Escalation.incident_number` is nullable —
  some escalations are account-level, not incident-specific).
- SysUser records belong to zero or one AssignmentGroup; `Incident.assigned_to` and
  `Incident.assignment_group` stay free-text/name references, not enforced foreign keys, mirroring
  how `mock-jira`'s Issue keeps `assignee`/`reporter` as free text rather than a User FK.

### Invariants

- `incident.number` is stable and never renumbered once seeded or created — it is the identifier
  `portwell-portal` tests key on for the ten narrative tickets.
- `incident.state` is always one of `new`, `in_progress`, `on_hold`, `resolved`, `closed`; the API
  rejects any other value.
- `incident.priority` is always an integer 1 to 4.
- `task_sla.business_time_only` is `true` for resolution SLAs (this is the seeded discrepancy's
  mechanism, not a bug — see constitution Non-Negotiable Principle 6).
- Two of the five seeded Escalations have `owner: null`; this must survive every reseed.
- A small number of seeded Incidents are `resolved` with their `first_response` TaskSla still
  `has_breached: true`; this must survive every reseed.
- The MCP-facing write operations this API exposes (`update_incident`, `add_work_note` via
  `mcp-server`) apply no permission or state-transition guard at this layer either — see
  constitution Non-Negotiable Principle 5. This API itself never adds one.

## Capability Map

| Capability | Description | Priority | Milestone | Status |
|-----------|-------------|----------|-------|--------|
| List/get Incident | List Incidents (filterable by `account_id`, `state`, `category`, `opened_after`, `opened_before`, `escalated`; paginated), fetch one by number | must-have | mvp | validated |
| Create/update Incident | Create an Incident; update `state`, `priority`, `assigned_to`, `assignment_group` — unguarded | must-have | mvp | validated |
| List/add Work Notes | List an Incident's work notes; post a new one as any author, any note_type — unguarded | must-have | mvp | validated |
| List/get/update Escalations | List (filterable by `account_id`, `open_only`), fetch, and update Escalations | must-have | mvp | validated |
| Create Escalation | Server-assigns `number`/`opened_at`; client supplies `account_id`, `summary`, optional `incident_number`/`owner` — mirrors `POST /incidents`' server-assigned-identifier pattern | must-have | v2 | review-passed |
| List SLA records | List Task SLA records (filterable by `incident_number`, `breached`, `sla_definition`) | must-have | mvp | validated |
| List users and assignment groups | List the support-team directory | must-have | mvp | validated |
| Seed fixture data | Idempotent seed command populating all six tables from the sources PRD.md names, preserving the ten narrative tickets and the three seeded discrepancies | must-have | mvp | validated |
| OpenAPI contract | Auto-generated, browsable API documentation | should-have | mvp | planned |
| End-to-end API test suite | Real HTTP calls over a real socket against a live server process | must-have | v1.1 | validated |

## Deferred Capabilities

| Capability | Reason | Target Milestone | Depends On |
|-----------|--------|-------------|------------|
| Delete Incident/Escalation | No consumer requires it; ITSM tickets are never hard-deleted in practice | v2 | — |
| Create/delete SysUser or AssignmentGroup via API | The support team roster is fixed course fixture data; no consumer needs to mutate it | v2 | — |

## Interface Contracts

### Exposed APIs

| Interface | Type | Description |
|-----------|------|-------------|
| `GET /` | REST endpoint | Health and version |
| `GET /incidents` | REST endpoint | List Incidents, filtered and paginated |
| `GET /incidents/{number}` | REST endpoint | Fetch one Incident |
| `POST /incidents` | REST endpoint | Create an Incident |
| `PATCH /incidents/{number}` | REST endpoint | Update `state`/`priority`/`assigned_to`/`assignment_group` — unguarded |
| `GET /incidents/{number}/work_notes` | REST endpoint | List an Incident's work notes |
| `POST /incidents/{number}/work_notes` | REST endpoint | Add a work note — unguarded author/note_type |
| `GET /escalations` | REST endpoint | List Escalations, filtered |
| `GET /escalations/{number}` | REST endpoint | Fetch one Escalation |
| `POST /escalations` | REST endpoint | Create an Escalation — server-assigned `number`/`opened_at` |
| `PATCH /escalations/{number}` | REST endpoint | Update an Escalation |
| `GET /sla` | REST endpoint | List Task SLA records, filtered |
| `GET /users` | REST endpoint | List SysUsers |
| `GET /assignment_groups` | REST endpoint | List AssignmentGroups |
| `GET /openapi.json` | REST endpoint | Auto-generated OpenAPI contract document |

### Consumed APIs

None — this module has no inbound dependency on any other module or repo, per the project
constitution's first non-negotiable principle.

## Quality Attributes

| Attribute | Requirement |
|-----------|-------------|
| Performance | 1,307 incidents / 2,614 work notes is enough that an unpaginated list endpoint is a mistake worth letting students make once; pagination is required on every list endpoint. No explicit latency target beyond that. |
| Availability | Runs as a single local process; no HA requirement. Restarting it is an acceptable recovery path — Module 4 explicitly wants the API to be able to go down mid-run. |
| Security | No real auth. Bound to localhost only by default — never exposed to a real network, and no code path reaches a real network endpoint. |
| Observability | Errors return JSON with a message naming what was rejected and why. No structured logging required beyond what aids local debugging. |
