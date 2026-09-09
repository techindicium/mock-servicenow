---
charter: agent-ui
kind: behavioral
status: implemented
risk_level: low
revision: 1
charter-revision: 28
amends: .context-index/specs/features/agent-ui/escalations-directory-nav.spec.md
target-revision: 3
created: 2026-09-09
updated: 2026-09-09
source-manifest:
  sha: "c527d9f"
  files:
    - static/index.html
    - static/js/escalations-logic.js
    - static/js/escalations.js
    - tests_e2e/test_ui_create_escalation_e2e.py
    - tests_js/escalations-beh-6-7-create-payload.test.js
    - tests_js/escalations-beh-8-validation.test.js
  computed-at: "2026-09-09T21:20:54.193Z"
---

# Amendment: Live Spec: Escalations screen, directory screen, and navigation shell (targeting rev 3)

> This spec **amends** `.context-index/specs/features/agent-ui/escalations-directory-nav.spec.md` targeting revision 3.
> The base spec is immutable; this artifact carries the delta and is
> reviewed, planned, and validated on its own lifecycle.

## Amendment Rationale

The base spec's Preconditions list only `itsm-api`'s `escalations` and `user-directory` specs as
reachable dependencies, and its Behaviors (BEH-1..BEH-5) cover list, edit, and directory — no
create affordance. The agent-ui charter's Deferred Capabilities table carried "Escalation create"
pending `itsm-api`'s `POST /escalations` landing. `itsm-api`'s `escalations-rev-2-create-escalation`
amendment has since shipped and validated that endpoint (`ESCALATION-NNNN` server-assigned
`number`/`opened_at`, `account_id`/`summary` required, `incident_number`/`owner` optional). The
agent-ui charter (revision 28) now promotes "Create escalation" from Deferred Capabilities to an
active Capability Map row (should-have, milestone v2). This amendment adds the "New Escalation"
form to the Escalations screen, closing out that dependency.

## Behavioral Delta

### Superseded Precondition

None of the base spec's preconditions are contradicted — `POST /escalations` is additive to the
`escalations` interface the base spec already depends on. This amendment adds one new
precondition:

- `itsm-api`'s `escalations-rev-2-create-escalation` amendment is implemented and reachable —
  `POST /escalations` exists at the same origin this UI is served from.

### New Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-6** — **When** the viewer opens the "New Escalation" form on the Escalations view (a
  persistent affordance on that view, not a separate nav item) and submits it with `account_id`
  and `summary` filled in, **then** the UI calls `POST /escalations` with exactly those two
  fields, and on a `201` response prepends the returned Escalation (server-assigned `number` and
  `opened_at`, `incident_number: null`, `owner: null`, `closed_at: null`) to the list without a
  full page reload, and clears the form.
- **BEH-7** — **When** the viewer additionally fills in the form's optional `incident_number`
  and/or `owner` fields before submitting, **then** the UI includes those fields in the
  `POST /escalations` request body and renders the values the API returns for them — the API is
  the source of truth for what was actually stored, not the form's local input state.
- **BEH-8** — **When** the viewer submits the "New Escalation" form with `account_id` or
  `summary` left blank, **then** the UI does not call `POST /escalations` and instead shows an
  inline validation message naming the missing field(s) — the same required-field pattern the
  existing create-incident form already uses, per the base charter's Invariant that the UI never
  invents its own enum values but client-side required-field checks are expected before a network
  call.
- **BEH-9** — **When** a `POST /escalations` request from this form fails (network error or
  non-2xx response, including a `422` naming missing fields the client-side check did not catch),
  **then** the UI shows a visible message naming what failed, reusing BEH-5's error-surfacing
  behavior — the form is not cleared and the entered values remain so the viewer can retry.

### Postconditions (additive)

- A newly created Escalation from BEH-6/BEH-7 is immediately visible in the Escalations view's
  list and via a subsequent `GET /escalations`, consistent with the base spec's BEH-3 edit
  postcondition — no eventual-consistency window.
- A failed create (BEH-8/BEH-9) never adds a row to the visible list — only a server-confirmed
  `201` response does.

### Error Cases (additive)

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| "New Escalation" form submitted with `account_id` or `summary` blank | Inline validation message naming the missing field(s); no request sent | `UI_VALIDATION_FAILED` |
| `POST /escalations` fails (network error or non-2xx) | Visible error message naming the failed action; form values retained | `UI_FETCH_FAILED` |

## System Constitution Reference

- **Principle 4:** "The HTTP contract is the boundary." — Applies because the new form reads and
  writes only through `itsm-api`'s documented `POST /escalations` endpoint, never a direct
  database access.
- **Principle 6:** "Seeded discrepancies are load-bearing, not bugs." — Applies because BEH-7
  passes `incident_number`/`owner` through unmodified and renders back exactly what the API
  stored, never defaulting or hiding a null the way the base spec's BEH-2/BEH-3 already require
  for the list/edit paths.
- **Principle 5:** "The MCP tools stay unguarded." — Applies by extension: this create form is a
  thin, unguarded pass-through to `POST /escalations`, consistent with how the base spec's BEH-3
  and `incident-console.spec.md`'s create-incident form treat writes — client-side required-field
  checks (BEH-8) are a usability nicety, not a permission or business-rule guard the API itself
  doesn't already enforce (the API's own `422` in BEH-9 is the real guard).

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| "New Escalation" form markup | Add form (`account_id`, `summary` required; `incident_number`, `owner` optional) to the Escalations view | small |
| Create-escalation wiring | Client-side required-field check, `POST /escalations` call, prepend result to list, clear form on success | medium |
| Error surfacing | Reuse BEH-5's visible-error pattern for validation and fetch failures, retaining form values on failure | small |

## Acceptance Criteria

- [ ] Submitting the form with only `account_id`/`summary` creates an Escalation and prepends it to the list with server-assigned `number`/`opened_at` and null `incident_number`/`owner`/`closed_at` (BEH-6)
- [ ] Submitting with `incident_number`/`owner` filled in sends and renders them exactly as the API returns them (BEH-7)
- [ ] Submitting with `account_id` or `summary` blank shows inline validation and sends no request (BEH-8)
- [ ] A failed `POST /escalations` shows a visible error and retains the entered form values (BEH-9)
- [ ] A created Escalation is visible without a full page reload and without waiting for a manual refresh
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
