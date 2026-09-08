---
charter: agent-ui
status: validated
risk_level: medium
milestone: mvp
revision: 2
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
source-manifest:
  sha: "f659bde"
  files:
    - .context-index/governance/gates.yaml
    - app/main.py
    - static/css/console.css
    - static/index.html
    - static/js/incident-logic.js
    - static/js/incident.js
    - tests/test_static_assets.py
    - tests_js/beh-1-list-load.test.js
    - tests_js/beh-2-list-filters.test.js
    - tests_js/beh-3-record-view.test.js
    - tests_js/beh-4-work-note-timeline.test.js
    - tests_js/beh-5-add-work-note.test.js
    - tests_js/beh-6-sla-panel.test.js
    - tests_js/beh-7-edit-incident.test.js
    - tests_js/beh-8-create-incident.test.js
    - tests_js/beh-9-error-formatting.test.js
  computed-at: "2026-09-08T14:00:59.175Z"
---

# Live Spec: Incident console (list, record view, work notes, SLA, editing, create)

<!-- Live Spec within the agent-ui charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/agent-ui/charter.md -->

## Behavioral Contract

### Preconditions

- `itsm-api`'s `incident-lifecycle`, `work-notes`, and `sla-records` specs are implemented and
  reachable — this UI is served by that same process, so its API calls are same-origin relative
  requests (`/incidents`, `/sla`), no base URL configuration needed.
- This spec's edits to an Incident (`PATCH /incidents/{number}`) and its work-note additions
  (`POST /incidents/{number}/work_notes`) apply no permission check, confirmation dialog, or
  state-transition guard beyond what `itsm-api` itself enforces — per constitution Non-Negotiable
  Principle 5, this UI never adds a write guard the API and MCP layers intentionally omit.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** the incident list page loads with no filters applied, **then** it fetches
  `GET /incidents` (default page) and renders each Incident's `number`, `short_description`,
  `state`, `priority`, `category`, `account_id`, and `escalated` flag in a paginated table/list,
  with pagination controls reflecting the API's `page`/`page_size`/`total` response fields.
- **BEH-2** — **When** the viewer sets any combination of the `state`, `category`, `account_id`,
  `escalated` filters, **then** the list re-fetches `GET /incidents` with those query parameters
  and re-renders, fully replacing the previously shown page — it never merges an old and new
  filter's results on screen at once.
- **BEH-3** — **When** the viewer opens an Incident from the list, **then** the record view
  fetches `GET /incidents/{number}` and renders every field, including `null` fields
  (`assigned_to`, `assignment_group`, `resolved_at`) as an explicit "unassigned"/"not resolved"
  state, never omitted or coerced to a placeholder value.
- **BEH-4** — **When** the record view loads, **then** it also fetches
  `GET /incidents/{number}/work_notes` and renders every WorkNote in chronological order, showing
  `created_by`, `note_type`, `body`, and `created_at` for each.
- **BEH-5** — **When** the viewer submits the add-work-note form with `created_by`, `note_type`,
  and `body` filled in, **then** the UI calls `POST /incidents/{number}/work_notes` with exactly
  those values — `created_by` is a free-text field, never constrained to a picker of known users
  or the currently "logged in" identity (there is none) — and on success appends the new note to
  the visible timeline without a full page reload.
- **BEH-6** — **When** the record view loads, **then** it also fetches
  `GET /sla?incident_number={number}` and renders each returned TaskSla row's `sla_definition`,
  `target_minutes`, `actual_minutes`, `has_breached`, and `business_time_only`, with a visibly
  distinct (but not blocking or apologetic) treatment for `has_breached: true` rows — a breach is
  shown as a fact, never hidden, and never annotated as an error the UI caught.
- **BEH-7** — **When** the viewer edits `state`, `priority`, `assigned_to`, or `assignment_group`
  on the record view and saves, **then** the UI calls `PATCH /incidents/{number}` with exactly the
  changed fields and re-renders the updated record on success — **including a transition that
  resolves or closes the Incident while its `first_response` TaskSla shows `has_breached: true`,
  or while no customer-facing work note exists** — with no confirmation dialog, no warning
  banner, and no client-side check blocking or flagging the save. The save either succeeds (200)
  or fails with the API's own validation error (422) surfaced per BEH-9 — there is no third,
  UI-invented outcome.
- **BEH-8** — **When** the viewer submits the create-incident form with all six required fields
  (`account_id`, `category`, `short_description`, `description`, `state`, `priority`), **then**
  the UI calls `POST /incidents` and, on success, navigates to the new Incident's record view.
- **BEH-9** — **When** any API request in this spec fails (network error, or a non-2xx response
  such as a 422 validation error or 404 unknown incident), **then** the UI shows a visible message
  naming what failed and, for a 422, naming the invalid field the API's error body identifies —
  it never fails silently, shows a blank screen, or swallows the error.

### Postconditions

- Every user-supplied free-text field this spec renders (`short_description`, `description`,
  work-note `created_by` and `body`) is inserted as text (via `textContent`/safe DOM APIs), never
  interpreted as HTML or script, in the list, record view, or work-note timeline — these fields
  are unvalidated content at the API layer (per `work-notes.spec.md` BEH-4's unguarded
  `created_by`), so this UI is the only place safe rendering can be enforced. This is a rendering
  discipline, not a new guard on the API/MCP write surface, which stays unguarded per Principle 5.
- The record view's visible state always matches the Incident's current server state after any
  successful edit or work-note addition — no stale render survives a successful save.
- No client-side validation in this spec rejects an input the API itself would accept, and no
  client-side check accepts an input the API would reject silently (the API's own 422 response is
  always the final word — see BEH-9).
- Switching which Incident is open, or reapplying list filters, never leaves a previous
  Incident's or filter's data visibly mixed with the new selection.

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Any API request fails (network error or 5xx) | Visible error message naming the failed action | `UI_FETCH_FAILED` |
| `PATCH`/`POST` returns 422 | Visible error message naming the invalid field, from the API's own error body | `UI_VALIDATION_ERROR` |
| `GET /incidents/{number}` returns 404 | Visible "incident not found" message, not a blank or broken record view | `UI_NOT_FOUND` |

## System Constitution Reference

- **Principle 5:** "The MCP tools stay unguarded... Building safety around them is the exercise."
  — Applies directly to BEH-7: this UI's edit form is exactly as unguarded as the HTTP API and
  the MCP `update_incident`/`add_work_note` tools it sits beside; adding a confirmation dialog or
  client-side transition guard here would contradict the same principle that forbids it at the
  API and MCP layers.
- **Principle 6:** "Seeded discrepancies are load-bearing, not bugs." — Applies directly to BEH-6:
  a breached SLA or a resolved-with-open-breach Incident is rendered factually, never hidden,
  filtered, or flagged as a UI-detected error.
- **Principle 4:** "The HTTP contract is the boundary." — Applies because every read and write in
  this spec goes through `itsm-api`'s documented endpoints, never a direct database access.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Static shell + shared fetch/render helpers | HTML page skeleton (a single "Incidents" view container — no nav-item markup or view-switching logic; `escalations-directory-nav.spec.md` owns the nav rail and adds the Escalations/Directory items and switching behavior on top of this skeleton), shared JS fetch wrapper (error handling per BEH-9, rendering via `textContent`/safe DOM APIs, never raw HTML interpolation of API-returned strings), shared CSS | medium |
| Incident list view | Filter controls, paginated fetch/render, list-to-record navigation | medium |
| Incident record view | Field rendering including null-handling, work-note timeline render | medium |
| Add work note | Form + `POST` wiring, optimistic timeline append | small |
| SLA panel | Fetch/render TaskSla rows on the record view | small |
| Edit incident fields | Inline/form editing + `PATCH` wiring, unguarded | medium |
| Create incident | Form + `POST` wiring + navigation on success | small |

## Acceptance Criteria

- [ ] Incident list loads and renders a paginated, unfiltered page by default (BEH-1)
- [ ] Filters re-fetch and fully replace the list, never merging results (BEH-2)
- [ ] Opening an Incident renders every field, with null fields shown explicitly (BEH-3)
- [ ] The work-note timeline renders in chronological order with all fields (BEH-4)
- [ ] Adding a work note posts exactly the entered fields and appends to the timeline (BEH-5)
- [ ] The SLA panel renders every TaskSla row, breaches shown factually (BEH-6)
- [ ] Editing and saving incident fields is fully unguarded, including resolve-with-open-breach (BEH-7)
- [ ] Creating an incident posts all six fields and navigates to the new record (BEH-8)
- [ ] Every API failure surfaces a visible, specific message, never a silent failure (BEH-9)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
