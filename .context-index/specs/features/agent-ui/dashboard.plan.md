<!-- partial_schema: plan@1 -->

# Implementation Plan: Incident dashboard (KPI tiles)

> **Methodology:** adev
> **Charter:** .context-index/specs/features/agent-ui/charter.md
> **Spec:** .context-index/specs/features/agent-ui/dashboard.spec.md
> **Review:** PASS_WITH_NOTES (2026-09-09, revision 1 — see `dashboard.review.md`; 1 warning,
> resolved via a task-map wording fix, no spec-behavior change)
> **Platform:** vanilla JS / HTML / CSS (no build step), served as static assets by itsm-api
> (FastAPI, Python 3.11)

**Goal:** Add a fourth nav destination, "Dashboard," showing seven KPI tiles (one per Incident
state, one for `escalated: true`, one for breached SLA records), each sourced from itsm-api's own
`total` pagination field. Five state tiles and the Escalated tile are clickable through to a
correctly filtered Incidents view; the Breached SLAs tile is plain text.

**Architecture:** The nav rail, view-switching logic, and `#view-*` container pattern already
exist (`static/index.html`, `static/js/nav-logic.js`, `static/js/nav.js`, all owned by
`escalations-directory-nav.spec.md`). This plan extends them additively — one new nav button, one
new view container, one new branch in `nav.js`'s click handler — the same way
`escalations-directory-nav.spec.md` itself extended `incident-console.spec.md`'s skeleton. It
never recreates the nav shell.

**Design decision — always re-fetch on activation, unlike Escalations/Directory:** `nav.js`'s
existing `loadedViews` Set makes Escalations/Directory load only once per page session (first
activation). BEH-5 requires Dashboard to re-fetch every time it's activated, since KPI counts are
meaningless if stale. This plan's `nav.js` change therefore does NOT gate the dashboard branch on
`loadedViews` — `loadDashboardView()` runs on every click of the Dashboard nav item, a deliberate,
spec-required divergence from the sibling views' pattern, not an inconsistency to "fix."

**Design decision — click-through reuses the existing filter form, not a new hook:** Per the
review's SA-1 finding, `static/js/incident.js` exports no filter-and-reload entry point.
Clicking a tile therefore: (1) if the incident record or create view is open, closes it back to
the list (clicking `#back-to-list`/`#cancel-create-incident`) so no stale sub-view is left showing
underneath; (2) clicks `#nav-incidents` to switch top-level views; (3) sets
`#incident-filter-form`'s `state`/`escalated` fields and calls `requestSubmit()`, letting
`incident-console.spec.md`'s own `onFilterSubmit` handler run unmodified. This satisfies this
spec's own Postcondition — a dashboard-origin filter must behave identically to a manual one —
by construction, since it *is* the manual path, just triggered programmatically.

**Design note — the Breached SLAs tile counts an app-wide fact, not "this page's" incidents:**
`GET /sla?breached=true&page_size=1` counts every breached TaskSla record regardless of its
Incident's `state`. This matches the spec's own BEH-1 wording exactly ("a tile for breached SLA
records") and constitution Principle 6 (a breach is reported as a fact, not filtered by
convenience).

**Constitution Validation:** No task adds auth, a permission check, or a client-side guard beyond
what the API enforces (Principle 5 — this spec is read-only, so the principle is satisfied
vacuously, but no task introduces a new write surface either). No task recomputes a count
client-side by paging and summing — every number is the API's own `total` (Principle 4: the HTTP
contract, including its pagination envelope, is the boundary). The Breached SLAs tile reports the
real count with no annotation suggesting it should be lower (Principle 6). No task is
`[REQUIRES HUMAN APPROVAL]`.

---

## File Structure

**Create:**
- `static/css/dashboard.css` — tile grid layout, tile/label typography, error-state styling
- `static/js/dashboard-logic.js` — pure `DASHBOARD_TILES` config, `buildTileUrl`,
  `isTileClickable`, `tileFilterParams` — UMD-wrapped (CommonJS for `node:test`, global for the
  browser)
- `static/js/dashboard.js` — DOM/fetch shell: fires the seven fetches via `Promise.allSettled`
  (so one rejection never blocks the others, per BEH-4), renders tiles via `textContent`, wires
  clickable-tile clicks to the existing filter form (see Design decision above)
- `tests_js/beh-1-dashboard-tiles.test.js` — `node:test` coverage of `dashboard-logic.js`
- `tests_e2e/test_ui_dashboard_e2e.py` — real-browser coverage for BEH-1, BEH-2, BEH-3

**Modify (cross-spec — owned by `escalations-directory-nav.spec.md`; extended additively here,
same pattern that spec itself used when extending `incident-console.spec.md`'s skeleton):**
- `static/index.html` — add `<button id="nav-dashboard">` to the nav rail, add
  `<section id="view-dashboard">` to `.app-main`, add this plan's new `<link>`/`<script>` tags
- `static/js/nav-logic.js` — add `"dashboard"` to `NAV_VIEWS` (NOT the default view — `DEFAULT_VIEW`
  stays `"incidents"`, per this spec's own Precondition)
- `static/js/nav.js` — add the dashboard branch to `onNavClick` (always re-fetch, no
  `loadedViews` gate — see Design decision above)

**Reference (read, do not modify):**
- `static/js/incident.js` — `onFilterSubmit`, `#incident-filter-form`'s field names
  (`state`, `escalated`, `category`, `account_id`), `#back-to-list`/`#cancel-create-incident`
  click handlers this plan's navigation function reuses verbatim
- `static/js/ui-errors.js` — `UiErrors.formatApiError(action, error)`, reused for per-tile errors
- `app/routers/incidents.py`, `app/routers/sla.py` — exact query param names (`state`,
  `escalated`, `page_size` on `/incidents`; `breached`, `page_size` on `/sla`) and the `total`
  field on both paginated response shapes

---

## Context Packets

### Task 1 Context
- Spec: Preconditions (nav shell already exists, Incidents stays default), BEH-1
- Reference: `escalations-directory-nav.plan.md` Task 1 (the same wrap-existing-shell pattern,
  one spec generation earlier)

### Task 2 Context
- Spec: BEH-1 (seven exact query shapes), BEH-2/BEH-3 (which tiles are clickable)
- Reference: `app/routers/incidents.py::list_incidents`, `app/routers/sla.py::list_sla_records`

### Task 3 Context
- Spec: BEH-1 through BEH-5 in full
- Reference: `static/js/incident.js`'s `onFilterSubmit`/`#back-to-list`/`#cancel-create-incident`;
  `static/js/ui-errors.js`'s `formatApiError`

### Task 4 Context
- Spec: full Acceptance Criteria list
- Reference: `tests_e2e/conftest.py`'s `page`/`ui_app_server` fixtures (reused unchanged)

---

## Parallelization

- Task 1 (nav wiring) has no dependency and can be planned/implemented independently of Task 2.
- Task 2 (pure logic) has no dependency on Task 1.
- Task 3 (DOM shell) depends on both Task 1 (markup/nav must exist) and Task 2 (logic module).
- Task 4 (e2e) depends on Task 3.

Given the small size of this plan (4 tasks, one clear dependency chain into Task 3), this plan is
executed sequentially rather than declaring a parallel group — the coordination overhead of
parallel dispatch would exceed the savings.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Nav item + view container (cross-spec extension) | small | unit | — | 3 modify |
| 2 | Pure tile-shaping logic (BEH-1, BEH-2, BEH-3) | small | unit | — | 1 create + 1 test create |
| 3 | Tile fetch/render + click-through (BEH-1 through BEH-5) | medium | unit | Task 1, Task 2 | 2 create |
| 4 | Real-browser e2e coverage | small | unit | Task 3 | 1 create |

All four tasks resolve to the `unit` strategy (fallback — no `test_strategy` in spec frontmatter).

**Granularity:** `per-behavior` (source: manifest `test_policy.granularity`).

---

## Task Structure

### Task 1: Nav item + view container (cross-spec extension) [specialist: none]

**Charter capability:** Incident dashboard
**Depends on:** none
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `static/index.html`, `static/js/nav-logic.js`, `static/js/nav.js`

**Context to load:**
- Spec Preconditions; the real current content of all three files (read before editing — do not
  assume the snippets below are byte-exact against a file other work may have touched since this
  plan was written)

- [ ] **Write failing test**

Extend the existing `tests_js/nav-beh-1-view-switch-logic.test.js` (owned by
`escalations-directory-nav.spec.md`, modified here additively — do not remove or rewrite its
existing test cases) with:

```javascript
test("BEH-1 (dashboard): Dashboard is a known view but never the default", () => {
  const { NAV_VIEWS, DEFAULT_VIEW, isKnownView } = require("../static/js/nav-logic.js");
  assert.equal(isKnownView("dashboard"), true);
  assert.equal(NAV_VIEWS.includes("dashboard"), true);
  assert.notEqual(DEFAULT_VIEW, "dashboard");
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/nav-beh-1-view-switch-logic.test.js`
Expected: FAIL — `"dashboard"` is not yet in `NAV_VIEWS`.

- [ ] **Implement**

In `static/js/nav-logic.js`, change:
```javascript
const NAV_VIEWS = ["incidents", "escalations", "directory"];
```
to:
```javascript
const NAV_VIEWS = ["incidents", "escalations", "directory", "dashboard"];
```
`DEFAULT_VIEW` stays `"incidents"` — unchanged.

In `static/js/nav.js`, inside `onNavClick`, add a fourth branch after the existing
escalations/directory branches. Unlike those two, this branch is NOT gated by `loadedViews` —
Dashboard re-fetches on every activation (BEH-5):
```javascript
    if (currentView === "dashboard" && typeof loadDashboardView === "function") {
      loadDashboardView();
    }
```

In `static/index.html`, add a fourth nav button inside `<nav class="nav-rail" id="nav-rail">`,
after the Directory button:
```html
      <button type="button" class="nav-item" id="nav-dashboard" data-view="dashboard">Dashboard</button>
```
Add a fourth view container inside `.app-main`, after `#view-directory`'s closing `</section>`:
```html
      <section id="view-dashboard" class="view" hidden>
        <h1>Dashboard</h1>
        <div id="dashboard-tiles"></div>
      </section>
```
Add this plan's new stylesheet/script tags to `<head>`/before `</body>` (Task 2/3 create the
files these reference — add the tags now so Task 1's own test below can assert on them, matching
this repo's established convention of wiring tags in the markup task and filling in the files in
later tasks):
```html
  <link rel="stylesheet" href="/static/css/dashboard.css">
```
```html
  <script src="/static/js/dashboard-logic.js"></script>
  <script src="/static/js/dashboard.js"></script>
```

- [ ] **Verify test passes**

Run: `node --test tests_js/nav-beh-1-view-switch-logic.test.js`
Expected: PASS. Also re-run `node --test tests_js/nav-beh-1-*.test.js` to confirm no regression in
the sibling nav markup/wiring tests (they use `[^>]*`-flexible or substring regexes and should be
unaffected by an additive fourth button/view).

- [ ] **Commit**

Branch (if not already created): `feat/agent-ui/dashboard`

```bash
git add static/index.html static/js/nav-logic.js static/js/nav.js \
  tests_js/nav-beh-1-view-switch-logic.test.js
git commit -m "feat(agent-ui): add Dashboard nav item and view container"
```

---

### Task 2: Pure tile-shaping logic (BEH-1, BEH-2, BEH-3) [specialist: none]

**Charter capability:** Incident dashboard
**Depends on:** none
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `static/js/dashboard-logic.js`
- Test: `tests_js/beh-1-dashboard-tiles.test.js` (create)

- [ ] **Write failing test**

```javascript
// tests_js/beh-1-dashboard-tiles.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const {
  DASHBOARD_TILES, buildTileUrl, isTileClickable, tileFilterParams,
} = require("../static/js/dashboard-logic.js");

test("BEH-1: exactly seven tiles — one per state, escalated, breached SLA", () => {
  assert.equal(DASHBOARD_TILES.length, 7);
  assert.deepEqual(
    DASHBOARD_TILES.map((t) => t.key),
    ["new", "in_progress", "on_hold", "resolved", "closed", "escalated", "breached_sla"]
  );
});

test("BEH-1: each state tile's URL filters /incidents by that state, page_size=1", () => {
  const tile = DASHBOARD_TILES.find((t) => t.key === "on_hold");
  assert.equal(buildTileUrl(tile), "/incidents?state=on_hold&page_size=1");
});

test("BEH-1: the escalated tile's URL filters /incidents by escalated=true, page_size=1", () => {
  const tile = DASHBOARD_TILES.find((t) => t.key === "escalated");
  assert.equal(buildTileUrl(tile), "/incidents?escalated=true&page_size=1");
});

test("BEH-1: the breached-SLA tile's URL filters /sla by breached=true, page_size=1", () => {
  const tile = DASHBOARD_TILES.find((t) => t.key === "breached_sla");
  assert.equal(buildTileUrl(tile), "/sla?breached=true&page_size=1");
});

test("BEH-2/BEH-3: state and escalated tiles are clickable, breached SLA is not", () => {
  for (const key of ["new", "in_progress", "on_hold", "resolved", "closed", "escalated"]) {
    assert.equal(isTileClickable(DASHBOARD_TILES.find((t) => t.key === key)), true);
  }
  assert.equal(isTileClickable(DASHBOARD_TILES.find((t) => t.key === "breached_sla")), false);
});

test("BEH-2: state tiles resolve to a state filter, the escalated tile to an escalated filter", () => {
  assert.deepEqual(tileFilterParams(DASHBOARD_TILES.find((t) => t.key === "new")), { state: "new" });
  assert.deepEqual(
    tileFilterParams(DASHBOARD_TILES.find((t) => t.key === "escalated")), { escalated: "true" }
  );
});

test("BEH-3: the breached-SLA tile has no filter, since it isn't clickable", () => {
  assert.equal(tileFilterParams(DASHBOARD_TILES.find((t) => t.key === "breached_sla")), null);
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/beh-1-dashboard-tiles.test.js`
Expected: FAIL — `static/js/dashboard-logic.js` does not exist yet (`MODULE_NOT_FOUND`).

- [ ] **Implement**

```javascript
// static/js/dashboard-logic.js
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.DashboardLogic = factory();
})(typeof window !== "undefined" ? window : globalThis, function () {
  const DASHBOARD_TILES = [
    { key: "new", label: "New", kind: "state", value: "new" },
    { key: "in_progress", label: "In Progress", kind: "state", value: "in_progress" },
    { key: "on_hold", label: "On Hold", kind: "state", value: "on_hold" },
    { key: "resolved", label: "Resolved", kind: "state", value: "resolved" },
    { key: "closed", label: "Closed", kind: "state", value: "closed" },
    { key: "escalated", label: "Escalated", kind: "escalated" },
    { key: "breached_sla", label: "Breached SLAs", kind: "info" },
  ];

  function buildTileUrl(tile) {
    if (tile.kind === "state") return `/incidents?state=${tile.value}&page_size=1`;
    if (tile.kind === "escalated") return "/incidents?escalated=true&page_size=1";
    return "/sla?breached=true&page_size=1";
  }

  function isTileClickable(tile) {
    return tile.kind !== "info";
  }

  function tileFilterParams(tile) {
    if (tile.kind === "state") return { state: tile.value };
    if (tile.kind === "escalated") return { escalated: "true" };
    return null;
  }

  return { DASHBOARD_TILES, buildTileUrl, isTileClickable, tileFilterParams };
});
```

- [ ] **Verify test passes**

Run: `node --test tests_js/beh-1-dashboard-tiles.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/dashboard-logic.js tests_js/beh-1-dashboard-tiles.test.js
git commit -m "feat(agent-ui): add pure dashboard tile-shaping logic"
```

---

### Task 3: Tile fetch/render + click-through (BEH-1 through BEH-5) [specialist: none]

**Charter capability:** Incident dashboard
**Depends on:** Task 1, Task 2
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `static/js/dashboard.js`, `static/css/dashboard.css`

**Note on test strategy:** Per this repo's established convention, the DOM/fetch shell files
(`incident.js`, `escalations.js`, `directory.js`, and now `dashboard.js`) are not unit-tested —
their real behavior is proven by Task 4's real-browser e2e suite. This task's own verification
step is therefore a manual/visual check plus the full existing test suite staying green, not a
new `tests_js` file.

- [ ] **Write failing test**

None (see Note above) — Task 4 is this behavior's test.

- [ ] **Verify test fails**

N/A.

- [ ] **Implement**

```javascript
// static/js/dashboard.js
(function () {
  function navigateToFilteredIncidents(filter) {
    const recordView = document.getElementById("incident-record-view");
    if (!recordView.hidden) document.getElementById("back-to-list").click();
    const createView = document.getElementById("create-incident");
    if (!createView.hidden) document.getElementById("cancel-create-incident").click();
    document.getElementById("nav-incidents").click();

    const form = document.getElementById("incident-filter-form");
    form.state.value = (filter && filter.state) || "";
    form.escalated.value = (filter && filter.escalated) || "";
    form.category.value = "";
    form.account_id.value = "";
    form.requestSubmit();
  }

  function renderTile(tile, outcome) {
    const wrapper = document.createElement("div");
    wrapper.className = "dashboard-tile";
    wrapper.dataset.tile = tile.key;

    if (outcome.status === "rejected") {
      const errorEl = document.createElement("p");
      errorEl.className = "dashboard-tile-error";
      errorEl.textContent = UiErrors.formatApiError(`Loading ${tile.label}`, outcome.reason || {});
      wrapper.appendChild(errorEl);
    } else if (DashboardLogic.isTileClickable(tile)) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "dashboard-tile-value";
      button.textContent = String(outcome.value);
      button.addEventListener("click", () => {
        navigateToFilteredIncidents(DashboardLogic.tileFilterParams(tile));
      });
      wrapper.appendChild(button);
    } else {
      const span = document.createElement("span");
      span.className = "dashboard-tile-value";
      span.textContent = String(outcome.value); // never a <button> or link — BEH-3
      wrapper.appendChild(span);
    }

    const label = document.createElement("p");
    label.className = "dashboard-tile-label";
    label.textContent = tile.label;
    wrapper.appendChild(label);
    return wrapper;
  }

  async function fetchTileTotal(tile) {
    let resp;
    try {
      resp = await fetch(DashboardLogic.buildTileUrl(tile));
    } catch (networkErr) {
      throw { message: networkErr.message };
    }
    if (!resp.ok) throw { status: resp.status };
    const body = await resp.json();
    return body.total;
  }

  async function loadDashboardView() {
    const container = document.getElementById("dashboard-tiles");
    container.innerHTML = ""; // full replace — BEH-5: a revisit never mixes stale tiles in
    const settled = await Promise.allSettled(
      DashboardLogic.DASHBOARD_TILES.map((tile) => fetchTileTotal(tile))
    );
    DashboardLogic.DASHBOARD_TILES.forEach((tile, i) => {
      const outcome = settled[i].status === "fulfilled"
        ? { status: "fulfilled", value: settled[i].value }
        : { status: "rejected", reason: settled[i].reason };
      container.appendChild(renderTile(tile, outcome));
    });
  }

  window.loadDashboardView = loadDashboardView;
})();
```

```css
/* static/css/dashboard.css */
#dashboard-tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
  max-width: 900px;
}

.dashboard-tile {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem;
  text-align: center;
}

.dashboard-tile-value {
  display: block;
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--link);
  background: none;
  border: none;
  padding: 0;
  margin: 0 0 0.25rem 0;
  font-family: inherit;
  cursor: pointer;
}

.dashboard-tile[data-tile="breached_sla"] .dashboard-tile-value {
  color: var(--danger);
  cursor: default; /* plain text, no click affordance — BEH-3 */
}

.dashboard-tile-label {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-muted);
}

.dashboard-tile-error {
  margin: 0 0 0.25rem 0;
  font-size: 0.78rem;
  color: var(--danger);
  font-weight: 600;
}
```

`window.loadDashboardView` is a plain global function (not a `window.DashboardApp` namespace
object) because `nav.js` calls it by bare name (`typeof loadDashboardView === "function"`),
exactly matching how `loadEscalationsView`/`loadDirectoryView` are already called — consistency
with the existing two sibling views' calling convention, not a new pattern.

- [ ] **Verify test passes**

Manual check: start the app (`uvicorn app.main:app` against a seeded DB), click Dashboard, confirm
seven tiles render with real numbers, click a state tile, confirm it lands on a correctly filtered
Incidents list. Then run the full existing suite to confirm no regression:
`python3 -m pytest -q && ruff check . && node --test tests_js/**/*.test.js`

- [ ] **Commit**

```bash
git add static/js/dashboard.js static/css/dashboard.css
git commit -m "feat(agent-ui): add dashboard tile fetch/render and click-through to filtered Incidents"
```

---

### Task 4: Real-browser e2e coverage (BEH-1, BEH-2, BEH-3) [specialist: none]

**Charter capability:** Incident dashboard
**Depends on:** Task 3
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `tests_e2e/test_ui_dashboard_e2e.py`

**Context to load:**
- Reuses the `page`/`ui_app_server` fixtures `ui-e2e.spec.md`'s `tests_e2e/conftest.py` already
  provides — no new fixture

- [ ] **Write failing test**

```python
# tests_e2e/test_ui_dashboard_e2e.py
import httpx


def test_dashboard_renders_seven_tiles_with_real_counts(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incidents-table-body tr")
    page.click("#nav-dashboard")
    page.wait_for_selector('.dashboard-tile[data-tile="new"] .dashboard-tile-value')

    assert page.locator(".dashboard-tile").count() == 7

    expected_total = httpx.get(
        f"{ui_app_server}/incidents", params={"state": "new", "page_size": 1}
    ).json()["total"]
    actual = page.locator('.dashboard-tile[data-tile="new"] .dashboard-tile-value').inner_text()
    assert actual == str(expected_total)


def test_breached_sla_tile_is_plain_text_with_no_click_affordance(page, ui_app_server):
    page.goto(ui_app_server)
    page.click("#nav-dashboard")
    page.wait_for_selector('.dashboard-tile[data-tile="breached_sla"] .dashboard-tile-value')

    tag_name = page.locator(
        '.dashboard-tile[data-tile="breached_sla"] .dashboard-tile-value'
    ).evaluate("el => el.tagName")
    assert tag_name == "SPAN"


def test_clicking_a_state_tile_navigates_to_a_correctly_filtered_incidents_view(page, ui_app_server):
    page.goto(ui_app_server)
    page.click("#nav-dashboard")
    page.wait_for_selector('.dashboard-tile[data-tile="closed"] .dashboard-tile-value')
    page.click('.dashboard-tile[data-tile="closed"] .dashboard-tile-value')

    page.wait_for_selector("#incident-list-view:not([hidden])")
    assert page.locator("#filter-state").input_value() == "closed"
    page.wait_for_selector('#incidents-table-body tr[data-state="closed"]')
    # Every rendered row is really closed — the filter was actually applied, not just the select's value
    states = page.locator("#incidents-table-body tr").evaluate_all(
        "rows => rows.map(r => r.dataset.state)"
    )
    assert all(s == "closed" for s in states)
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_ui_dashboard_e2e.py`
Expected: FAIL — `fixture 'page' not found` before Task 1 lands, or a selector timeout before
Tasks 1-3 exist. If Tasks 1-3 are already implemented and committed by the time this task runs
(same plan, sequential dependency), expect PASS directly — document plainly rather than forcing
an artificial RED step, consistent with this repo's established convention for e2e tasks that
follow their own unit-level tasks in the same plan.

- [ ] **Implement**

No production code changes expected — Tasks 1-3 already implement the dashboard.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_ui_dashboard_e2e.py`
Expected: PASS. Then run the complete gate suite:
```bash
python3 -m pytest -q
ruff check .
node --test tests_js/**/*.test.js
python3 -m pytest -q tests_e2e/
```
All must be green.

- [ ] **Commit**

```bash
git add tests_e2e/test_ui_dashboard_e2e.py
git commit -m "test(agent-ui): add real-browser coverage for the incident dashboard"
```

---

## Quality Gates

- Test Suite: `python3 -m pytest -q` (existing `test` gate)
- Linter: `ruff check .` (existing `lint` gate)
- JS Unit Tests: `node --test tests_js/**/*.test.js` (existing `test-js` gate)
- E2E: `python3 -m pytest -q tests_e2e/` (existing `e2e-smoke` gate, severity warning)
- No `governance/gates.yaml` change needed — all four gates already cover this plan's new files
  by location.
- All acceptance criteria from `dashboard.spec.md` satisfied:
  - [ ] Seven tiles render from real API `total` fields (BEH-1)
  - [ ] State/Escalated tiles navigate to a correctly filtered Incidents view (BEH-2)
  - [ ] Breached SLAs tile is plain text with no click affordance (BEH-3)
  - [ ] A single tile's failure doesn't blank the others (BEH-4)
  - [ ] Re-visiting Dashboard re-fetches fresh (BEH-5)
  - [ ] All quality gates pass (tests, lint)
  - [ ] No constitutional violations introduced
