# mock-servicenow, product requirements

**Status:** draft for review. Nothing built yet beyond the README.
**Audience:** whoever charters and implements this repo.

## What it is

A standalone mock of a ServiceNow-shaped ITSM API: incidents, work notes, assignment groups, and
SLA records. It is the system of record for Portwell's support desk.

Course infrastructure, not a course exercise. Students integrate against it; they do not build
it. It follows the same shape as `mock-jira`: FastAPI over SQLite, a thin MCP server in front,
two containers, no auth, no outbound network — plus a browser-facing agent workspace, same as
`mock-jira`'s kanban board, so the mock reads and feels like a real support desk to anyone
looking at it, not just to a program calling its API.

## Who consumes it

| Track | Uses it for | Module it first matters in |
| :- | :- | :- |
| `portwell-portal` (SDLC) | The support desk the Assist service reads tickets from and writes proposals against | 2 |
| `portwell-analytics` (DDLC) | The source it extracts ticket and interaction data from | 2 |
| `portwell-knowledge` (KDLC) | Open escalations and their ages, quoted in the monthly service review packs | 2 |

Three of four tracks. It is the most depended-on system in the course, which is why it is worth
building properly.

## Why it exists

Today those three repos read ticket data from a committed SQLite file and a CSV extract. That is
fine for modelling a lifecycle in Module 1 and useless for Module 2, where the subject is tool
mediation. A tool that reads a local file cannot fail interestingly, cannot half-succeed, and
cannot do something irreversible.

An ITSM API can do all three, and closing a ticket is exactly the kind of write that makes a
permission boundary real rather than theatrical.

## Non-goals

Not a ServiceNow clone, and not the real Now Platform's UI framework (UI Builder, Service Portal,
the actual ServiceNow client codebase). Explicitly out of scope: the ServiceNow scripting engine,
workflows-as-a-configurable-subsystem, CMDB, change management, catalogue items, approvals as a
subsystem, notifications, and anything requiring authentication.

A simplified agent workspace *is* in scope (see "Agent UI" below) — a real support desk has a UI
agents work tickets from, and a headless API alone reads as a program's mock, not a support
desk's. What stays out of scope is ServiceNow's actual UI *technology* and its configurability,
not the presence of a UI at all.

Out of scope for a different reason: the post-incident write-ups in each repo's
`docs/incidents/`. Those are documents a person wrote after the fact and they stay documents. The
incident *records* live here; the *reviews* do not.

## Data model

Six tables. Field names follow ServiceNow's conventions where the convention is recognisable,
because part of the point is that the API looks like something students will meet again.

### `incident`

The support ticket. 1,307 of them across June to August 2026.

| Field | Type | Notes |
| :- | :- | :- |
| `number` | text, PK | `TICKET-004417`. Matches the canon exactly; never renumbered. |
| `account_id` | text | `ACCOUNT-1001`. Reconciles with the canon and with mock-salesforce. |
| `category` | text | One of the eight product areas: receiving, putaway, picking, cycle-count, billing, integrations, auth, reporting |
| `short_description` | text | The subject line |
| `description` | text | The body |
| `state` | text | `new`, `in_progress`, `on_hold`, `resolved`, `closed` |
| `priority` | int | 1 to 4 |
| `opened_at` | ISO timestamp | |
| `resolved_at` | ISO timestamp, nullable | |
| `assigned_to` | text, nullable | A person's name, per the canon |
| `assignment_group` | text | |
| `escalated` | bool | |

### `work_note`

One row per message or action on an incident. 2,614 of them. The grain first-response time is
computed from.

| Field | Type | Notes |
| :- | :- | :- |
| `sys_id` | text, PK | `INTERACTION-0100001` |
| `incident_number` | text, FK | |
| `created_at` | ISO timestamp | |
| `created_by` | text | `customer`, an agent name, or `assist` |
| `note_type` | text | `comment`, `work_note`, `state_change`, `proposal_sent` |
| `body` | text | |

### `escalation`

Five seeded, open, with real ages. The reporting packs quote these and nothing verifies them.

| Field | Type | Notes |
| :- | :- | :- |
| `number` | text, PK | `ESCALATION-0412` |
| `incident_number` | text, FK, nullable | |
| `account_id` | text | |
| `summary` | text | |
| `opened_at` | ISO timestamp | |
| `closed_at` | ISO timestamp, nullable | |
| `owner` | text, nullable | Some have none. That is deliberate. |

### `task_sla`

**The most important table in this system, and the reason it is worth building.**

Today, SLA attainment is computed by the analytics warehouse from interaction timestamps, and the
reporting packs quote that figure. In real ServiceNow, SLA is a first-class record the platform
maintains. Putting it here means the pack's central number has a *source* that can be checked,
and a computed figure disagreeing with the system of record becomes a real, findable problem
rather than a hypothetical one.

| Field | Type | Notes |
| :- | :- | :- |
| `sys_id` | text, PK | |
| `incident_number` | text, FK | |
| `sla_definition` | text | `first_response`, `resolution` |
| `target_minutes` | int | From the account's tier |
| `actual_minutes` | int, nullable | |
| `has_breached` | bool | |
| `business_time_only` | bool | Set true for resolution SLAs. See the seeded discrepancy below. |

### `sys_user` and `assignment_group`

The support team, per the canon. Nine support people plus the named individuals. Groups:
`Support Tier 1`, `Support Tier 2`, `Solution Consultants`.

## API surface

REST, JSON, no auth. Paths follow the existing mocks' plain style rather than ServiceNow's
`/api/now/table/...`, because the latter buys nothing here.

```
GET    /                                  health and version
GET    /incidents                         filter: account_id, state, category, opened_after,
                                          opened_before, escalated; paginated
GET    /incidents/{number}
POST   /incidents
PATCH  /incidents/{number}                state, priority, assigned_to, assignment_group
GET    /incidents/{number}/work_notes
POST   /incidents/{number}/work_notes
GET    /escalations                       filter: account_id, open_only
GET    /escalations/{number}
PATCH  /escalations/{number}
GET    /sla                               filter: incident_number, breached, sla_definition
GET    /users
GET    /assignment_groups
```

Pagination on every list endpoint. 1,307 incidents is enough that an unpaginated fetch is a
mistake worth letting students make once.

## MCP tools

Thin wrappers, same as mock-jira. Nine tools:

`list_incidents`, `get_incident`, `create_incident`, `update_incident`, `list_work_notes`,
`add_work_note`, `list_escalations`, `list_sla_records`, `list_users`

**Deliberately unguarded.** `update_incident` can move any incident to any state, including
resolving one that has an open SLA breach or an unanswered customer. `add_work_note` can post as
any author, including `assist`.

That is the point. Activity 2 asks groups to build safe tool definitions with explicit permission
boundaries and failure behaviour. The exercise is building a constrained wrapper over these, not
connecting to them. A guarded MCP would remove the exercise.

## Agent UI

A browser-facing support-desk workspace, same shape as `mock-jira`'s kanban board: static
HTML/CSS/JS served by `itsm-api`'s own FastAPI process (same origin, same container — no
separate service, no CORS, no runtime base-URL config). It is a pure client of the REST API
above; it owns no data of its own and never touches the database directly.

- **Incident console.** A filterable, paginated incident list (by `state`, `category`,
  `account_id`, `escalated`) and a record view per incident showing every field, its work-note
  timeline (chronological, author and type visible), and a form to add a work note as any author.
  The state/priority/assigned_to/assignment_group fields are editable inline or via a form that
  calls `PATCH /incidents/{number}` — exactly as unguarded as the API and the MCP tools it sits
  beside. The UI adds no confirmation step, no permission check, and no warning banner that the
  API and MCP layers don't already have; it is a window onto the same unguarded surface, not a
  new boundary.
- **Escalations screen.** List all five, including the two ownerless ones exactly as `owner: null`
  (never hidden or defaulted to a placeholder), with a simple form to edit `summary`/`owner`/
  `closed_at` via `PATCH /escalations/{number}`.
- **SLA panel.** On the incident record view, the incident's `task_sla` rows (first_response,
  resolution) with target/actual minutes and breach status, shown factually — no annotation
  claiming a breach is wrong, since `business_time_only` disagreements are a seeded discrepancy,
  not a bug the UI should paper over.
- **Directory screen.** Read-only list of `sys_user`/`assignment_group` (`GET /users`,
  `GET /assignment_groups`) — no create/edit, since the API doesn't support them.

Out of scope for this UI: login/auth (nothing to log into), real-time/websocket sync (reload or
polling is enough), drag-and-drop kanban-style board (incidents don't have a small fixed status
set the way `mock-jira`'s issues do — five states plus escalation flag reads better as a list/
detail pair than a column board), and any write action the REST API doesn't already expose
(no incident/escalation create-and-delete beyond what's listed above).

## Seed data

Loaded from the existing fixtures so nothing has to be re-invented and the current defects carry
over.

| From | Into | Rows |
| :- | :- | :- |
| `portwell-portal/data/seed/history/tickets.csv` | `incident` | 1,307 |
| `portwell-portal/data/seed/history/interactions.csv` | `work_note` | 2,614 |
| `portwell-knowledge` pack escalation sheets | `escalation` | 5 |
| Derived from tier commitments and work-note timestamps | `task_sla` | one or two per incident |
| `course-shared/canon/company.md` | `sys_user`, `assignment_group` | ~12 |

The ten narrative tickets keep their exact identifiers and content, because tests in
`portwell-portal` key on them.

Seeding must be a documented command that runs from a clean container, and re-running it must be
idempotent.

## What the course needs it to make possible

| Module | What it enables |
| :- | :- |
| 1 | Not used. Module 1 stays file-only so week one cannot fail on Docker. |
| 2 | A real tool boundary. Reads are safe; `update_incident` and `add_work_note` are not. A group builds a constrained wrapper and a hook that intercepts writes. |
| 3 | `POLICY-01` becomes enforceable at a real boundary: refuse to resolve a billing incident for a Business or Enterprise account where no human work note exists. |
| 4 | Failure modes a file cannot produce: the API being down mid-run, a partial page fetch, a write that succeeded while the response was lost. |

## Seeded discrepancies

Three, all of which should be present from the first seed and none of which should be documented
anywhere participants can read.

1. **The SLA disagreement.** `task_sla.actual_minutes` for resolution SLAs is measured in business
   hours; the analytics warehouse computes elapsed wall-clock. For accounts with weekend tickets
   the two disagree, and the reporting pack quotes the warehouse figure. Neither is wrong. Nobody
   has noticed they are different measures.

2. **Escalations with no owner.** Two of the five have `owner` null. The packs quote the count and
   the age; nothing asks who is chasing them.

3. **Resolved with an open breach.** A large share of incidents — driven honestly by the account
   mix (three Enterprise accounts, each with a 30-minute first-response commitment, account for
   most historical volume) and the desk's own documented performance (`course-shared/canon
   /company.md`: median first response is 94 minutes, already past the laxer Business-tier
   60-minute commitment) — are `resolved` while their `first_response` SLA record shows
   `has_breached` true. The desk closed them; the SLA record was never revisited. This is not a
   rare edge case in the real data: computed honestly, it is closer to the norm than the
   exception, which is itself the finding worth surfacing in Module 2-4 exercises rather than a
   count to engineer down to something smaller.

Record all three in `course-shared/heldout/seeded-defects.md` when seeding lands.

## Deployment

Two containers, same as the others. **Ports must not collide with the existing mocks**, which
both default to 8000 and 8001:

| Service | Port |
| :- | -: |
| `itsm-api` | 8030 |
| `mcp-server` | 8031 |

The port assignment for every mock belongs in `adev-workspace.yaml`, and the other two repos need
moving off 8000/8001 in the same change.

## Acceptance

- `docker compose up` on a clean checkout brings both services healthy.
- The seed command loads all five tables and is idempotent.
- `GET /incidents?account_id=ACCOUNT-1001&opened_after=2026-08-01` returns the same set the
  analytics warehouse returns for that filter.
- The MCP server lists nine tools over streamable-http at `/mcp`.
- No endpoint requires auth and no code path reaches a real network endpoint.
- The three seeded discrepancies are present and reproducible.
- The agent UI, served from `itsm-api` at `/`, lets a person browse incidents, open one, read its
  work-note timeline and SLA status, add a work note, change its state/priority/assignment, and
  browse escalations and the support directory — entirely by clicking, no HTTP client needed.
