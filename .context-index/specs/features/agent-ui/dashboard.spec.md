---
charter: agent-ui
status: validated
risk_level: medium
milestone: v1.2
revision: 1
charter-revision: 22
created: 2026-09-09
updated: 2026-09-09
kind: behavioral
source-manifest:
  sha: "dd88ebc"
  files:
    - static/css/dashboard.css
    - static/index.html
    - static/js/dashboard-logic.js
    - static/js/dashboard.js
    - static/js/nav-logic.js
    - static/js/nav.js
    - tests_e2e/test_ui_dashboard_e2e.py
    - tests_js/beh-1-dashboard-tiles.test.js
    - tests_js/nav-beh-1-view-switch-logic.test.js
  computed-at: "2026-09-09T11:24:07.643Z"
---

# Live Spec: Incident dashboard (KPI tiles)

<!-- Live Spec within the agent-ui charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/agent-ui/charter.md -->

## Behavioral Contract

### Preconditions

- `escalations-directory-nav.spec.md`'s nav shell exists — this spec adds a fourth nav item
  ("Dashboard") and a fourth top-level view container on top of that shell, the same way
  `escalations-directory-nav.spec.md` itself added two view containers on top of
  `incident-console.spec.md`'s skeleton. It does not rebuild the nav shell.
- This spec never counts records by paging through and summing client-side — every tile's number
  comes directly from the itsm-api response's own `total` pagination field, fetched with
  `page_size=1` so the response body carries at most one record's worth of payload.
- "Incidents" remains the default active view on first load (unchanged from
  `escalations-directory-nav.spec.md` BEH-1) — this spec adds Dashboard as a fourth, non-default
  nav destination, not a replacement default.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** the viewer selects the "Dashboard" nav item, **then** the UI issues seven
  parallel `GET` requests — `GET /incidents?state=new&page_size=1`,
  `GET /incidents?state=in_progress&page_size=1`, `GET /incidents?state=on_hold&page_size=1`,
  `GET /incidents?state=resolved&page_size=1`, `GET /incidents?state=closed&page_size=1`,
  `GET /incidents?escalated=true&page_size=1`, `GET /sla?breached=true&page_size=1` — and renders
  one tile per request showing that response's `total` value and a label naming what it counts.
- **BEH-2** — **When** the viewer clicks a state tile (New / In Progress / On Hold / Resolved /
  Closed) or the Escalated tile, **then** the UI switches to the Incidents view with that state
  (or `escalated=true`) applied as the active filter and the list re-fetched accordingly — the
  same filtering mechanism `incident-console.spec.md` BEH-2 already implements, driven
  programmatically instead of through the filter form.
- **BEH-3** — **When** the dashboard renders, **then** the Breached SLAs tile is plain text (its
  number and label), never a `<button>` or a link, and it has no click handler — there is no
  Incidents-list filter for "has a breached SLA," so this tile does not imply a navigation
  affordance the UI cannot honor.
- **BEH-4** — **When** any of the seven dashboard requests fails (network error or non-2xx
  response), **then** that specific tile shows a visible "failed to load" state naming what
  failed, while the other tiles that did succeed still render their real counts — one failed
  request never blanks the whole dashboard.
- **BEH-5** — **When** the viewer returns to the Dashboard view after visiting another view,
  **then** all seven counts are re-fetched fresh (no stale cached numbers from the first visit),
  consistent with every other view in this app re-fetching on activation.

### Postconditions

- The seven counts always reflect the live server state at the time the Dashboard view was last
  activated — this spec never invents a client-side cache with its own invalidation logic.
- Clicking a clickable tile (BEH-2) leaves the Incidents view in exactly the same state a manual
  filter-form submission with that value would — no separate "dashboard-origin" code path with
  different behavior.

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Any of the seven dashboard requests fails (network error or 5xx) | That tile shows a visible "failed to load" message naming the tile; other tiles are unaffected | `UI_FETCH_FAILED` |

## System Constitution Reference

- **Principle 4:** "The HTTP contract is the boundary." — Applies because every count in this spec
  comes from itsm-api's own `total` field on a real request, never a locally recomputed sum.
- **Principle 6:** "Seeded discrepancies are load-bearing, not bugs." — Applies to the Breached
  SLAs tile: it reports the real breached count (a seeded discrepancy) as a plain fact, with no
  annotation suggesting it is wrong or should be corrected.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Nav item + view container | Add "Dashboard" nav item and `#view-dashboard` container to the existing shell (modifies `static/index.html`, `static/js/nav-logic.js`, `static/js/nav.js` — all owned by `escalations-directory-nav.spec.md`; this spec extends them additively) | small |
| Tile fetch/render logic | Pure `dashboard-logic.js` shaping seven parallel-fetch results into tile view-models (label, value, clickable filter or none) | medium |
| Tile DOM/fetch shell + click-through | `dashboard.js`: fires the seven fetches, renders tiles via `textContent`. Click-through drives the *existing* filter form and nav, not a new entry point: populate `#incident-filter-form`'s `state`/`escalated` field and call the form's `requestSubmit()` (so `incident-console.spec.md`'s own `onFilterSubmit` handler runs unmodified), then dispatch a `click` on `#nav-incidents` to switch views — the same mechanism a person clicking through the UI manually would trigger, satisfying this spec's own Postcondition that a dashboard-origin filter behaves identically to a manual one | medium |
| Error handling | Per-tile failure state, reusing `UiErrors.formatApiError` | small |

## Acceptance Criteria

- [ ] Dashboard renders seven tiles sourced from real API `total` fields, never a client-side count (BEH-1)
- [ ] The five state tiles and the Escalated tile navigate to a correctly filtered Incidents view on click (BEH-2)
- [ ] The Breached SLAs tile is plain text with no click affordance (BEH-3)
- [ ] A single tile's fetch failure shows a visible per-tile error without blanking the others (BEH-4)
- [ ] Re-visiting Dashboard re-fetches all seven counts fresh (BEH-5)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
