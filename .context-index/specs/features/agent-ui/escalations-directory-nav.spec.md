---
charter: agent-ui
status: validated
risk_level: low
milestone: mvp
revision: 2
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
source-manifest:
  sha: "bfe000f"
  files:
    - static/css/nav.css
    - static/index.html
    - static/js/directory-logic.js
    - static/js/directory.js
    - static/js/escalations-logic.js
    - static/js/escalations.js
    - static/js/nav-logic.js
    - static/js/nav.js
    - static/js/ui-errors.js
    - tests/test_nav_static_assets.py
    - tests_js/beh-5-error-formatting.test.js
    - tests_js/directory-beh-4-render-logic.test.js
    - tests_js/escalations-beh-2-render-logic.test.js
    - tests_js/escalations-beh-3-patch-payload.test.js
    - tests_js/nav-beh-1-markup.test.js
    - tests_js/nav-beh-1-view-switch-logic.test.js
    - tests_js/nav-beh-1-wiring.test.js
  computed-at: "2026-09-09T11:07:26.562Z"
---

# Live Spec: Escalations screen, directory screen, and navigation shell

<!-- Live Spec within the agent-ui charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/agent-ui/charter.md -->

## Behavioral Contract

### Preconditions

- `itsm-api`'s `escalations` and `user-directory` specs are implemented and reachable — this UI
  is served by that same process, so its API calls are same-origin relative requests.
- `incident-console.spec.md`'s static shell and shared fetch/render helpers exist — that spec
  builds only the page skeleton (a single "Incidents" view container) and shared JS/CSS
  utilities, with no nav-item markup or view-switching logic of its own. This spec is the one
  that adds the nav rail itself — its Escalations/Directory items, the Incidents item pointing at
  the existing skeleton, and the view-switching logic — on top of that skeleton, not a second one.
- Escalation `summary` and directory `name`/`role` are free-text fields with no auth boundary
  restricting who can set them (per constitution: no real auth anywhere in this system). This
  spec's rendering must insert them via `textContent`/safe DOM APIs, never raw HTML
  interpolation, to avoid a stored-XSS shape — a documentation nudge for how the UI renders
  API-returned strings, not a new guard on the API/MCP surface itself, which stays unguarded.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** the page loads or the viewer selects the "Incidents" / "Escalations" /
  "Directory" nav item, **then** the corresponding view container is shown and the other two are
  hidden — exactly one view is visible at a time, switched client-side with no full page reload.
  "Incidents" is the default active view on first load.
- **BEH-2** — **When** the Escalations view loads, **then** it fetches `GET /escalations` and
  renders every returned Escalation's `number`, `account_id`, `summary`, `opened_at`, `closed_at`,
  and `owner` — an `owner: null` row renders as an explicit "unassigned" state, never hidden or
  defaulted to a placeholder name. `incident_number` is deliberately not rendered in this list
  (matching the charter's escalations-screen scope); this view relies on the API's default page
  size covering the seeded five-row fixture set in a single page — this milestone adds no
  pagination controls here, unlike `incident-console.spec.md`'s BEH-1, since Escalation volume
  is fixed and small by design (see `itsm-api`'s escalations charter Preconditions).
- **BEH-3** — **When** the viewer submits the escalation edit form (`summary`/`owner`/`closed_at`)
  for one Escalation, **then** the UI calls `PATCH /escalations/{number}` with exactly the changed
  fields, including explicitly clearing `owner` to null when the viewer blanks that field out —
  the API's own acceptance of an explicit-null `owner` (see `escalations.spec.md` BEH-7) is not
  re-guarded here.
- **BEH-4** — **When** the Directory view loads, **then** it fetches `GET /users` and
  `GET /assignment_groups` and renders both lists (name/role/assignment_group for each SysUser;
  name for each AssignmentGroup) — read-only, no edit or create controls, since the API does not
  support them. As with BEH-2, this view relies on the default page size covering the seeded
  ~12-row directory in a single page; no pagination controls this milestone.
- **BEH-5** — **When** any API request in this spec fails (network error or non-2xx response),
  **then** the UI shows a visible message naming what failed — it never fails silently or shows a
  blank screen.

### Postconditions

- Switching between Incidents / Escalations / Directory never leaves a previous view's content
  visible underneath the newly active one.
- An Escalation edit saved via BEH-3 is immediately reflected in that view's list the next time
  it is fetched or refreshed, without requiring a full page reload.

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Any API request fails (network error or 5xx) | Visible error message naming the failed action | `UI_FETCH_FAILED` |
| `PATCH /escalations/{number}` returns 404 | Visible "escalation not found" message | `UI_NOT_FOUND` |

## System Constitution Reference

- **Principle 6:** "Seeded discrepancies are load-bearing, not bugs." — Applies directly to
  BEH-2: an ownerless Escalation renders exactly as such, never hidden or defaulted.
- **Principle 4:** "The HTTP contract is the boundary." — Applies because every read and write in
  this spec goes through `itsm-api`'s documented endpoints, never a direct database access.
- **Principle 5:** "The MCP tools stay unguarded." — Applies by extension to BEH-3: this UI's
  escalation edit is a thin, unguarded pass-through, consistent with how `incident-console.spec.md`
  treats Incident edits.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Navigation shell | Left-hand nav rail, client-side view-switching, Incidents default-active | small |
| Escalations view | Fetch/render list, edit form + `PATCH` wiring including explicit-null owner | medium |
| Directory view | Fetch/render read-only Users and AssignmentGroups lists | small |

## Acceptance Criteria

- [ ] Nav shell shows exactly one view at a time, Incidents active by default (BEH-1)
- [ ] Escalations view renders every row including ownerless ones explicitly (BEH-2)
- [ ] Escalation edit form saves changed fields, including explicit-null owner (BEH-3)
- [ ] Directory view renders Users and AssignmentGroups read-only (BEH-4)
- [ ] Every API failure surfaces a visible, specific message (BEH-5)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
