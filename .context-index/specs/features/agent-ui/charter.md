---
status: approved
kind: feature
revision: 31
updated: 2026-09-09
---

# Feature Charter: agent-ui

<!-- Feature Charter for the agent-ui module.
     This defines WHAT the module does and its boundaries, not HOW it is built.
     Live Specs within this charter define specific behavioral contracts. -->

## Business Intent

agent-ui gives `mock-servicenow` a support-desk workspace web interface — an incident console,
an escalations screen, and a support-directory screen — so the mock reads and feels like a real
ITSM desk to anyone browsing it, not just to a program calling its API or an agent calling its
MCP tools. It is a pure client of `itsm-api`: it owns no persisted data and never touches the
database directly. It ships as static assets (HTML/CSS/JS) served by `itsm-api`'s own HTTP
process — same origin, same container — so its API calls are same-origin relative requests with
no separate server, no CORS configuration, and no runtime base-URL configuration to wire up. This
mirrors `mock-jira`'s `kanban-ui` module exactly in shape and hosting model.

Per PRD.md's revised Non-goals: this module is explicitly in scope. What stays out of scope is
ServiceNow's actual UI technology (UI Builder, Service Portal) and its configurability, not the
presence of a UI at all — a real support desk has a UI agents work tickets from.

## Scope and Boundaries

### In Scope

- An incident console: a filterable (`state`, `category`, `account_id`, `escalated`), paginated
  list view, and a record (detail) view per incident showing every field.
- The record view's work-note timeline: every WorkNote for that incident, chronological, author
  and `note_type` visible, plus a form to add a new work note as any author (`created_by` is a
  free-text field, not a picker constrained to known users — matching the API's own unguarded
  `created_by` acceptance).
- Editing an incident's `state`, `priority`, `assigned_to`, `assignment_group` from the record
  view (inline controls or a form), calling `PATCH /incidents/{number}`. **Exactly as unguarded
  as the API and MCP tools it sits beside** — no confirmation dialog, no permission check, no
  warning banner blocking a state transition the API itself would accept. This UI is a window
  onto the same unguarded surface, not a new boundary; see Non-Negotiable Principle 5 in this
  repo's constitution.
- Creating an incident via a form (`POST /incidents`), all six required fields.
- An escalations screen: list all Escalations (including ownerless ones, `owner: null` rendered
  as-is, never hidden or defaulted to a placeholder), a form to edit `summary`/`owner`/
  `closed_at` via `PATCH /escalations/{number}`, and a "New Escalation" form calling
  `POST /escalations` (client supplies `account_id`, `summary`, optional `incident_number`/
  `owner`; the server assigns `number`/`opened_at`, mirroring the create-incident form's
  server-assigned-identifier pattern).
- An SLA panel on the incident record view: that incident's `task_sla` rows (`first_response`,
  `resolution`) with `target_minutes`/`actual_minutes`/`has_breached`/`business_time_only` shown
  factually — no annotation claiming a breach is "wrong" or filtering one out, since the
  business-hours/wall-clock disagreement and resolved-with-open-breach states are seeded
  discrepancies, not bugs the UI corrects or hides (constitution Principle 6).
- A directory screen: read-only list of `sys_user`/`assignment_group` (`GET /users`,
  `GET /assignment_groups`) — no create/edit, since the API doesn't support them.
- A persistent left-hand navigation shell (Incidents / Escalations / Directory / Dashboard) that
  switches between view containers client-side, mirroring `kanban-ui`'s nav-rail pattern.
- A dashboard screen: KPI tiles counting Incidents by `state` (one tile per state), a tile for
  `escalated: true` Incidents, and a tile for breached SLA records — each sourced from the API's
  own `total` pagination field (`page_size=1` per query), never computed by paging through and
  counting client-side. The five state tiles and the escalated tile are clickable and navigate to
  the Incidents view pre-filtered accordingly; the breached-SLA tile is informational only (no
  filter exists at the Incidents list level to jump to), and is rendered as plain text, never as a
  disabled-looking button, so it doesn't imply an affordance that isn't there.
- A "Related Escalation" panel on the incident record view: if any Escalation's `incident_number`
  matches the open Incident, its `number`/`summary`/`owner`/`closed_at` are shown; if none does,
  the panel still renders with an explicit "No related escalation" state — never omitted — per
  this charter's own Invariant that absence is always shown, not hidden.

### Out of Scope

- Authentication/login — there is no user model to log into.
- Real-time multi-user sync (websockets/live push). A page reload or simple polling is enough.
- A kanban-style drag-and-drop board — Incidents don't have the small fixed status set `mock-jira`
  Issues do (five states plus an independent `escalated` flag), which reads better as a
  list/detail pair than a column board; this is a deliberate divergence from `kanban-ui`'s shape,
  not an oversight.
- Any create/edit/delete the REST API doesn't already expose (e.g., deleting an
  Incident/Escalation, or creating/editing the SysUser/AssignmentGroup directory).
- Mobile-responsive polish — a desktop-width browser is the target.
- Adding any permission boundary, confirmation step, or state-transition guard the API doesn't
  already have — see In Scope's unguarded-editing note. Building that guard is a *consuming*
  track's exercise (Module 2), never this module's.

### Dependencies

| Dependency | Type | Description |
|-----------|------|-------------|
| itsm-api | internal module | Sole source of data, and the process that serves this module's static assets. All reads and writes go through its HTTP API; this module never opens the SQLite file directly. |

## Domain Model

<!-- This module owns no persisted entities — it renders itsm-api's Incident, WorkNote,
     Escalation, TaskSla, SysUser, and AssignmentGroup one-for-one. The one concept below is a
     pure view-side grouping, never persisted. -->

### Entities

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| IncidentListFilter | A client-side query-parameter set for the incident console's list view — not persisted, not an API resource | `state`, `category`, `account_id`, `escalated`, `page`, `page_size` |

### Relationships

- The incident console's record view loads one Incident plus its WorkNote timeline and TaskSla
  rows, via three separate itsm-api calls (`GET /incidents/{number}`,
  `GET /incidents/{number}/work_notes`, `GET /sla?incident_number={number}`).

### Invariants

- The UI never invents a `state`, `category`, or `note_type` value the API does not recognize —
  select/dropdown controls are populated from the same fixed enums the API validates against.
- Every Incident, Escalation, WorkNote, and TaskSla field the UI displays is rendered exactly as
  the API returns it — including `null` fields (`owner`, `assigned_to`, `resolved_at`) shown as
  an explicit empty/unassigned state, never coerced to a default value or omitted.

## Capability Map

| Capability | Description | Priority | Milestone | Status |
|-----------|-------------|----------|-------|--------|
| Incident list view | Filterable, paginated list of Incidents | must-have | mvp | validated |
| Incident record view | Full-detail view of one Incident | must-have | mvp | validated |
| Work-note timeline + add form | Chronological WorkNote list on the record view, plus an add-note form | must-have | mvp | validated |
| Edit incident fields | Inline/form editing of state/priority/assigned_to/assignment_group, unguarded | must-have | mvp | validated |
| Create incident | Form calling `POST /incidents` | must-have | mvp | validated |
| SLA panel | TaskSla rows shown on the incident record view | must-have | mvp | validated |
| Escalations screen | List + edit form for Escalations, ownerless rows shown as-is | must-have | mvp | validated |
| Create escalation | "New Escalation" form on the Escalations screen calling `POST /escalations`, server-assigned `number`/`opened_at` | should-have | v2 | implemented |
| Directory screen | Read-only Users/AssignmentGroups list | should-have | mvp | validated |
| App navigation shell | Persistent left-hand nav (Incidents / Escalations / Directory) | should-have | mvp | validated |
| End-to-end UI test suite | Real browser automation (a real rendering engine, real clicks/form fills) driving the actual served page — the same interface a person uses, never calling the UI's JS functions directly | must-have | v1.1 | validated |
| Incident dashboard | KPI tiles (per-state counts, escalated count, breached-SLA count) sourced from the API's own totals; state/escalated tiles clickable through to a filtered Incidents view | should-have | v1.2 | validated |
| Related escalation panel | Incident record view shows the matching Escalation (by `incident_number`) or an explicit "none" state | should-have | v1.2 | validated |

## Deferred Capabilities

| Capability | Reason | Target Milestone | Depends On |
|-----------|--------|-------------|------------|
| Real-time multi-viewer sync | No multi-user requirement yet; polling/reload suffices | v2 | — |
| Kanban-style board view | Incident's state model doesn't fit a small fixed-column board the way mock-jira's Issue does | — | — |

## Interface Contracts

### Exposed APIs

None — this module is consumed directly by a human through a browser, not programmatically by
other modules.

### Consumed APIs

| Interface | Source Module | Description |
|-----------|-------------|-------------|
| `GET /incidents` | itsm-api | Populate the incident list view |
| `GET /incidents/{number}` | itsm-api | Load the incident record view |
| `POST /incidents` | itsm-api | Create-incident form |
| `PATCH /incidents/{number}` | itsm-api | Save field edits on the record view — unguarded |
| `GET /incidents/{number}/work_notes` | itsm-api | Populate the work-note timeline |
| `POST /incidents/{number}/work_notes` | itsm-api | Add-work-note form — unguarded author |
| `GET /escalations` | itsm-api | Populate the escalations screen |
| `PATCH /escalations/{number}` | itsm-api | Escalations screen's edit form |
| `POST /escalations` | itsm-api | Escalations screen's "New Escalation" create form |
| `GET /sla` | itsm-api | Populate the SLA panel (filtered by `incident_number`) and the dashboard's breached-SLA tile (filtered by `breached=true`, `page_size=1`, reading only `total`) |
| `GET /users` | itsm-api | Populate the directory screen |
| `GET /assignment_groups` | itsm-api | Populate the directory screen |
| `GET /incidents` | itsm-api | Also used by the dashboard's per-state and escalated KPI tiles (`state=<x>` / `escalated=true`, `page_size=1`, reading only `total`) |
| `GET /escalations` | itsm-api | Also used by the incident record view's Related Escalation panel — the full (small, unpaged) fixture set is fetched and filtered client-side by `incident_number`, since the endpoint has no server-side `incident_number` filter |

## Quality Attributes

| Attribute | Requirement |
|-----------|-------------|
| Performance | List/record views render with no perceptible lag on a local connection at course-fixture volume (1,307 incidents, paginated). |
| Availability | No process of its own — availability is entirely itsm-api's, since that is what serves these static assets. Restarting that process is an acceptable recovery path. |
| Security | No real auth. Bound to localhost only by default — never exposed to a real network. Deliberately no write-guard — see Scope's unguarded-editing note. |
| Observability | API errors surface to the user as a visible message naming what failed; no structured logging required. |
