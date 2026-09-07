<!-- partial_schema: plan@1 -->

# Implementation Plan: Escalations screen, directory screen, and navigation shell

> **Methodology:** adev
> **Charter:** .context-index/specs/features/agent-ui/charter.md
> **Spec:** .context-index/specs/features/agent-ui/escalations-directory-nav.spec.md
> **Review:** PASS (2026-09-07, revision 2 — see `escalations-directory-nav.review.md`; 0
> blockers, 4 findings all resolved in revision 2)
> **Platform:** vanilla JS / HTML / CSS (no build step), served as static assets by itsm-api
> (FastAPI, Python 3.11) — per the charter's "mirrors `mock-jira`'s `kanban-ui` module exactly in
> shape and hosting model."

**Goal:** Add the persistent left-hand navigation shell (Incidents / Escalations / Directory)
that switches between client-side view containers with no full page reload, and build the
Escalations and Directory screens behind it — the escalations edit form (`PATCH`, including
explicit-null `owner`) and the read-only directory list (`GET /users`, `GET /assignment_groups`).

**Architecture:** Per the spec's own revision-2 Preconditions, `incident-console.spec.md` builds
only a static page skeleton (a single "Incidents" view container plus shared fetch/render
helpers) — no nav-item markup, no view-switching logic. This plan is the one that adds the nav
rail itself, on top of that skeleton, mirroring `mock-jira`'s `kanban-ui/app-navigation.plan.md`
shape (an `.app-shell` wrapper: `<nav class="nav-rail">` of three nav buttons, `.app-main` holding
three `<section class="view">` containers, one `showView`-style pure decision function, one DOM
wiring pass). No router library, no new dependency.

**Cross-plan coordination note (read before starting Task 1):** at the time this plan was
written, `incident-console.plan.md` did not yet exist as a file, and `static/`, `app/main.py`'s
static mount, and `tests_js/` do not yet exist in this repo (confirmed by directory listing).
This plan's Task 1 therefore proceeds on the spec's own stated dependency shape — `static/
index.html` with a single Incidents view, `static/js/incident-logic.js`/`incident.js`,
`app/main.py` serving `index.html` at `/` — and assumes the Incidents view container's id is
`view-incidents` (the naming convention this spec's own BEH-1 language and `mock-jira`'s
`view-board` precedent both point to). **Before implementing Task 1, the implementing agent must
re-read the actual `static/index.html` produced by `incident-console.plan.md` (it should exist by
then, per the two specs' stated build order) and adjust the wrap target id/selector if it differs
from `view-incidents`** — the wrap operation itself (add nav rail, relocate existing markup one
level deeper, add two new hidden view sections) does not change if the id differs, only the
literal selector used. This plan never recreates `static/index.html`, `incident-logic.js`, or
`incident.js` — it only adds to `index.html` and adds wholly new files alongside the existing
ones. `app/main.py` needs no change from this plan (no new API routes — this plan calls only the
already-implemented `GET /escalations`, `PATCH /escalations/{number}`, `GET /users`,
`GET /assignment_groups`), so it is a read-only reference here, not modified.

CSS is kept in a new `static/css/nav.css` file rather than merged into whatever CSS file
`incident-console.plan.md` creates — this avoids a same-file collision between two plans building
concurrently, at the cost of one extra `<link>` tag. `nav.css` covers the nav rail, `.app-shell`/
`.app-main` layout, and the two new views' list/form styling.

Escalations and Directory each get a pure-logic module (`escalations-logic.js`,
`directory-logic.js`) — row-shaping, the ownerless-owner-as-"Unassigned" display rule, and the
`PATCH` diff-payload builder (explicit-null `owner` included) — unit-tested via Node's `node:test`
runner with no DOM dependency, plus a thin DOM/fetch shell (`escalations.js`, `directory.js`)
that calls the logic module and inserts values via `textContent`/safe DOM APIs only, per the
spec's Preconditions (never raw HTML interpolation of `summary`/`name`/`role`). A shared
`ui-errors.js` pure formatter covers BEH-5's "name what failed" requirement consistently across
both screens' fetch/patch failures, including the escalation-not-found wording the spec's Error
Cases table requires verbatim.

**Constitution Validation:** No task adds auth, a permission check, a confirmation dialog, or a
client-side guard the API doesn't already enforce (Principle 5) — the escalation edit form is a
thin, unguarded pass-through to `PATCH /escalations/{number}`, exactly as `incident-console.plan.md`
treats Incident edits. No task corrects, hides, or annotates the two seeded ownerless escalations
(Principle 6) — `owner: null` always renders as an explicit "Unassigned" state. No task reaches a
database directly (Principle 4) — every read/write is a same-origin call to itsm-api's documented
endpoints. No task is `[REQUIRES HUMAN APPROVAL]`.

**Review notes carried forward:** revision 2's four findings (pagination-envelope note, the
deliberate `incident_number` omission, nav-shell ownership, and safe-DOM rendering) are all
spec-level and already resolved before this plan was written (see review file above) — no
outstanding review note applies to planning itself; each is reflected directly in the Architecture
notes above.

---

## File Structure

**Create:**
- `static/css/nav.css` — nav rail, `.app-shell`/`.app-main` layout, Escalations/Directory list and
  form styling
- `static/js/nav-logic.js` — pure view-switching decision logic (`resolveActiveView`,
  `viewVisibility`, `isKnownView`), UMD-wrapped (CommonJS for `node:test`, global for the browser)
- `static/js/nav.js` — DOM wiring: nav button click listeners, `showView(name)`, default-active
  wiring on page load, first-activation dispatch to `loadEscalationsView()`/`loadDirectoryView()`
- `static/js/ui-errors.js` — pure `formatApiError(action, error)` / `escalationNotFoundMessage
  (number)` formatters shared by both new screens' error handling
- `static/js/escalations-logic.js` — pure `escalationRowCells(escalation)` (ownerless →
  "Unassigned", `incident_number` deliberately excluded), `buildEscalationPatchPayload(original,
  edited)` (changed-fields-only diff, explicit-null `owner` support)
- `static/js/escalations.js` — DOM/fetch shell: `GET /escalations` on view load, renders rows via
  `textContent`, edit form wiring calling `PATCH /escalations/{number}`, error display
- `static/js/directory-logic.js` — pure `userRowCells(user)`, `groupRowCells(group)`
- `static/js/directory.js` — DOM/fetch shell: `GET /users` + `GET /assignment_groups` on view
  load, renders both lists via `textContent`, read-only (no edit/create controls), error display
- `tests_js/nav-beh-1-markup.test.js` — regex assertions on `static/index.html`: nav rail exists,
  three nav items, Incidents active by default, Escalations/Directory view containers exist hidden
- `tests_js/nav-beh-1-view-switch-logic.test.js` — `node:test` coverage of `nav-logic.js`
- `tests_js/nav-beh-1-wiring.test.js` — regex assertions on `static/js/nav.js` source: click
  listeners attached to all three nav ids, `showView` toggles `hidden`/`active`/`aria-current`
- `tests_js/escalations-beh-2-render-logic.test.js` — `node:test` coverage of
  `escalations-logic.js`'s row-shaping (ownerless → "Unassigned", no `incident_number` key)
- `tests_js/escalations-beh-3-patch-payload.test.js` — `node:test` coverage of
  `buildEscalationPatchPayload` (changed-fields-only, explicit-null `owner`)
- `tests_js/directory-beh-4-render-logic.test.js` — `node:test` coverage of `directory-logic.js`
- `tests_js/beh-5-error-formatting.test.js` — `node:test` coverage of `ui-errors.js`
- `tests/test_nav_static_assets.py` — pytest assertions that `static/index.html` references the
  new CSS/JS files and contains the nav rail and view-container markup this plan owns

**Modify:**
- `static/index.html` — add `.app-shell`/`<nav class="nav-rail">` wrapper around the existing
  Incidents view container (relocated one level deeper, not renamed), add
  `<section id="view-escalations" class="view" hidden>` and
  `<section id="view-directory" class="view" hidden>`, add `<link>`/`<script>` tags for this
  plan's new files. *(See Cross-plan coordination note above — created by `incident-console.plan.md`;
  this plan modifies it additively.)*

**Reference (read, do not modify):**
- `.context-index/specs/features/agent-ui/incident-console.plan.md` (once it exists) and
  `static/index.html`, `static/js/incident-logic.js`, `static/js/incident.js` it produces — the
  existing Incidents skeleton this plan wraps, never recreates
- `app/main.py` — serves `static/index.html` at `/` (per `incident-console.plan.md`'s expected
  shape); no change needed from this plan, since no new API route is added
- `app/routers/escalations.py`, `app/routers/directory.py`, `app/models.py` — the exact response
  shapes (`EscalationRead`/`EscalationPage`/`EscalationPatch`, `SysUserRead`/`PaginatedUsers`,
  `AssignmentGroupRead`/`PaginatedAssignmentGroups`) this plan's fetch code consumes verbatim
- `.context-index/specs/features/itsm-api/escalations.spec.md` BEH-6/BEH-7 (`PATCH` semantics,
  explicit-null `owner` acceptance), `user-directory.spec.md` BEH-1/BEH-2 (directory shape)
- `/Users/dpavancini/Development/adev-course/mock-jira/.context-index/specs/features/kanban-ui/app-navigation.plan.md`
  — the nav-rail-on-existing-shell pattern this plan mirrors (different repo; read-only reference)
- `/Users/dpavancini/Development/adev-course/mock-jira/static/js/board-logic.js`,
  `static/index.html`, `tests_js/navigation-beh-1-sidebar-markup.test.js` — pure-logic/UMD-module
  and markup-regex-test conventions this plan follows

---

## Context Packets

### Task 1 Context
- Spec: Preconditions (nav-shell ownership split with `incident-console.spec.md`); BEH-1 (exactly
  one view visible, Incidents default-active)
- Reference: `mock-jira/app-navigation.plan.md` Task 1 (wrap-existing-markup pattern);
  `incident-console.plan.md`'s actual `static/index.html` output (re-read before implementing)

### Task 2 Context
- Spec: BEH-1 ("the corresponding view container is shown and the other two are hidden — exactly
  one view is visible at a time")
- Reference: `mock-jira/board-logic.js`'s UMD wrapper shape

### Task 3 Context
- Spec: BEH-1 (client-side switching, no full page reload); Postconditions ("never leaves a
  previous view's content visible underneath")
- Reference: `mock-jira/board.js`'s `showView`/`onNavClick` pair; Task 2's `nav-logic.js`

### Task 4 Context
- Spec: Preconditions (`textContent`/safe-DOM rendering requirement); BEH-2 (`owner: null` →
  explicit "unassigned", `incident_number` deliberately excluded)
- Charter: Domain Model invariant ("every field... rendered exactly as the API returns it...
  including `null` fields... never coerced to a default value or omitted") — "Unassigned" is the
  spec-mandated explicit label, not a coercion, since BEH-2 names it directly
- Reference: `app/routers/escalations.py::list_escalations`, `EscalationRead`/`EscalationPage`

### Task 5 Context
- Spec: BEH-3 (`PATCH` with exactly changed fields, explicit-null `owner`); Postconditions (an
  edit is "immediately reflected... without requiring a full page reload")
- Reference: `escalations.spec.md` BEH-6/BEH-7 (API's own acceptance of explicit-null `owner`,
  not re-guarded here); `app/models.py::EscalationPatch`

### Task 6 Context
- Spec: BEH-4 (`GET /users` + `GET /assignment_groups`, read-only, no edit/create controls, "as
  with BEH-2, this view relies on the default page size")
- Reference: `app/routers/directory.py`, `SysUserRead`/`AssignmentGroupRead`/`PaginatedUsers`/
  `PaginatedAssignmentGroups`

### Task 7 Context
- Spec: BEH-5 ("any API request in this spec fails... shows a visible message naming what
  failed"); Error Cases table (`UI_FETCH_FAILED`, `UI_NOT_FOUND` with "escalation not found"
  wording for a 404 `PATCH`)
- Reference: Tasks 5-6's `escalations.js`/`directory.js` fetch call sites this task wires errors
  into

### Task 8 Context
- Spec: full Acceptance Criteria list
- Reference: `tests/test_directory.py`, `tests/test_escalations.py` (existing pytest conventions
  in this repo for asserting static/served content, if any exist by the time this task runs)

---

## Parallelization

- Group A (sequential): Task 1 → Task 2 → Task 3 → Task 4 (nav shell, in dependency order —
  markup before logic before wiring before styling-that-targets-the-wired-markup)
- Group B (each depends only on Group A's Task 1, for `view-escalations`/`view-directory`
  containers to exist; the two are otherwise independent and may run in parallel with each other
  and with the rest of Group A):
  - Task 5 (Escalations fetch/render + edit-form `PATCH` wiring)
  - Task 6 (Directory fetch/render)
- Task 7 (shared error-message wiring) depends on Task 5 and Task 6 both landing — it wires error
  handling into both screens' existing fetch/patch call sites.
- Task 8 (pytest static-assets + full regression) depends on all of Tasks 1-7.

**Depends on (cross-plan):** Task 1 depends on `incident-console.plan.md`'s task that produces
`static/index.html` with the Incidents view container and `app/main.py` serving it at `/`. This
plan cannot begin implementation until that lands (though it may be planned, as here, before that
sibling plan exists).

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Nav rail markup + wrap existing Incidents skeleton (BEH-1 markup) | small | unit | *(cross-plan)* incident-console skeleton | 1 modify (index.html) |
| 2 | Pure view-switching decision logic (BEH-1) | small | unit | Task 1 | 1 create + 1 test create |
| 3 | Nav DOM wiring: click handlers, default-active, no-reload switch (BEH-1) | small | unit | Task 1, Task 2 | 1 create + 1 test create |
| 4 | Nav rail / app-shell CSS | small | unit | Task 1, Task 3 | 1 create |
| 5 | Escalations view: fetch/render + edit-form `PATCH` wiring (BEH-2, BEH-3) | medium | unit | Task 1 | 2 create + 2 test create |
| 6 | Directory view: fetch/render Users + AssignmentGroups (BEH-4) | small | unit | Task 1 | 2 create + 1 test create |
| 7 | Shared error-message wiring across both screens (BEH-5, error cases) | small | unit | Task 5, Task 6 | 1 create + 1 test create |
| 8 | Static-assets pytest coverage + full regression pass | small | unit | Tasks 1-7 | 1 create |

All tasks resolve to the `unit` strategy (fallback — no `test_strategy` in spec frontmatter, no
matching `test_strategies` entries in `manifest.yaml`).

**Granularity:** `per-behavior` (source: manifest `test_policy.granularity`). Each BEH gets its own
test file (`nav-beh-1-*`, `escalations-beh-2-*`, `escalations-beh-3-*`, `directory-beh-4-*`,
`beh-5-*`), extended in place by later tasks that touch the same behavior rather than duplicated.

---

## Task Structure

### Task 1: Nav rail markup + wrap existing Incidents skeleton (BEH-1 markup) [specialist: none]

**Charter capability:** App navigation shell
**Depends on:** *(cross-plan)* `incident-console.plan.md`'s task producing `static/index.html`
with a single Incidents view container and `app/main.py` serving it at `/`.
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `static/index.html`
- Test: `tests_js/nav-beh-1-markup.test.js` (create)

**Context to load:**
- Spec Preconditions (nav-shell ownership), BEH-1
- The actual `static/index.html` produced by `incident-console.plan.md` — re-read before writing
  code; confirm the Incidents container's real id/selector matches the `view-incidents` assumption
  below and adjust if not

- [ ] **Write failing test**

```javascript
// tests_js/nav-beh-1-markup.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");

const html = readFileSync(require.resolve("../static/index.html"), "utf8");

test("BEH-1: nav rail exists with three nav items, Incidents active by default", () => {
  assert.match(html, /<nav class="nav-rail"/);
  assert.match(
    html,
    /<button type="button" class="nav-item active" id="nav-incidents" data-view="incidents"[^>]*>Incidents<\/button>/
  );
  assert.match(
    html,
    /<button type="button" class="nav-item" id="nav-escalations" data-view="escalations">Escalations<\/button>/
  );
  assert.match(
    html,
    /<button type="button" class="nav-item" id="nav-directory" data-view="directory">Directory<\/button>/
  );
});

test("Postconditions: existing Incidents skeleton is relocated, not renamed", () => {
  assert.match(html, /<section id="view-incidents" class="view">/);
});

test("BEH-1: Escalations/Directory view containers exist, hidden by default", () => {
  assert.match(html, /<section id="view-escalations" class="view" hidden>/);
  assert.match(html, /<section id="view-directory" class="view" hidden>/);
});

test("new stylesheet and scripts are wired in", () => {
  assert.match(html, /<link rel="stylesheet" href="\/static\/css\/nav\.css">/);
  assert.match(html, /<script src="\/static\/js\/nav-logic\.js"><\/script>/);
  assert.match(html, /<script src="\/static\/js\/nav\.js"><\/script>/);
  assert.match(html, /<script src="\/static\/js\/escalations-logic\.js"><\/script>/);
  assert.match(html, /<script src="\/static\/js\/escalations\.js"><\/script>/);
  assert.match(html, /<script src="\/static\/js\/directory-logic\.js"><\/script>/);
  assert.match(html, /<script src="\/static\/js\/directory\.js"><\/script>/);
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/nav-beh-1-markup.test.js`
Expected: FAIL — none of the nav rail markup, new view containers, or new `<link>`/`<script>`
tags exist yet in `static/index.html`.

- [ ] **Implement**

```html
<!-- static/index.html — wrap the existing Incidents skeleton, add nav rail + two new views -->
<head>
  <!-- ...existing incident-console <link>/<script> tags stay first, unmodified... -->
  <link rel="stylesheet" href="/static/css/nav.css">
</head>
<body>
  <div class="app-shell">
    <nav class="nav-rail">
      <button type="button" class="nav-item active" id="nav-incidents" data-view="incidents">Incidents</button>
      <button type="button" class="nav-item" id="nav-escalations" data-view="escalations">Escalations</button>
      <button type="button" class="nav-item" id="nav-directory" data-view="directory">Directory</button>
    </nav>
    <div class="app-main">
      <section id="view-incidents" class="view">
        <!-- ...incident-console.plan.md's existing markup, relocated here unchanged... -->
      </section>
      <section id="view-escalations" class="view" hidden>
        <div id="escalations-error" role="alert" hidden></div>
        <table id="escalations-table"><tbody></tbody></table>
        <form id="escalation-edit-form" hidden>
          <input type="hidden" name="number">
          <label>Summary <input type="text" name="summary"></label>
          <label>Owner <input type="text" name="owner"></label>
          <label>Closed at <input type="text" name="closed_at"></label>
          <button type="submit">Save</button>
        </form>
      </section>
      <section id="view-directory" class="view" hidden>
        <div id="directory-error" role="alert" hidden></div>
        <table id="users-table"><tbody></tbody></table>
        <table id="assignment-groups-table"><tbody></tbody></table>
      </section>
    </div>
  </div>
  <script src="/static/js/ui-errors.js"></script>
  <script src="/static/js/nav-logic.js"></script>
  <script src="/static/js/nav.js"></script>
  <script src="/static/js/escalations-logic.js"></script>
  <script src="/static/js/escalations.js"></script>
  <script src="/static/js/directory-logic.js"></script>
  <script src="/static/js/directory.js"></script>
</body>
```

- [ ] **Verify test passes**

Run: `node --test tests_js/nav-beh-1-markup.test.js`
Expected: PASS

- [ ] **Commit**

Branch (if not already created): `feat/agent-ui/escalations-directory-nav`

```bash
git add static/index.html tests_js/nav-beh-1-markup.test.js
git commit -m "feat(agent-ui): add nav rail markup and Escalations/Directory view containers"
```

---

### Task 2: Pure view-switching decision logic (BEH-1) [specialist: none]

**Charter capability:** App navigation shell
**Depends on:** Task 1
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `static/js/nav-logic.js`
- Test: `tests_js/nav-beh-1-view-switch-logic.test.js` (create)

- [ ] **Write failing test**

```javascript
// tests_js/nav-beh-1-view-switch-logic.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const {
  NAV_VIEWS,
  DEFAULT_VIEW,
  isKnownView,
  resolveActiveView,
  viewVisibility,
} = require("../static/js/nav-logic.js");

test("BEH-1: Incidents is the default active view", () => {
  assert.equal(DEFAULT_VIEW, "incidents");
  assert.deepEqual(NAV_VIEWS, ["incidents", "escalations", "directory"]);
});

test("BEH-1: exactly one view is visible for each known nav target", () => {
  for (const view of NAV_VIEWS) {
    const visibility = viewVisibility(view);
    assert.equal(Object.values(visibility).filter(Boolean).length, 1);
    assert.equal(visibility[view], true);
  }
});

test("BEH-1: an unrecognized target is a defensive no-op, staying on the current view", () => {
  assert.equal(resolveActiveView("kanban", "escalations"), "escalations");
  assert.equal(resolveActiveView("kanban", undefined), DEFAULT_VIEW);
});

test("BEH-1: a known target always becomes active", () => {
  assert.equal(resolveActiveView("directory", "incidents"), "directory");
  assert.equal(resolveActiveView("incidents", "directory"), "incidents");
});

test("isKnownView recognizes exactly the three nav targets", () => {
  assert.equal(isKnownView("incidents"), true);
  assert.equal(isKnownView("escalations"), true);
  assert.equal(isKnownView("directory"), true);
  assert.equal(isKnownView("kanban"), false);
  assert.equal(isKnownView(undefined), false);
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/nav-beh-1-view-switch-logic.test.js`
Expected: FAIL — `static/js/nav-logic.js` does not exist yet (`MODULE_NOT_FOUND`).

- [ ] **Implement**

```javascript
// static/js/nav-logic.js
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.NavLogic = factory();
  }
})(typeof window !== "undefined" ? window : globalThis, function () {
  const NAV_VIEWS = ["incidents", "escalations", "directory"];
  const DEFAULT_VIEW = "incidents";

  function isKnownView(view) {
    return NAV_VIEWS.includes(view);
  }

  function resolveActiveView(requestedView, currentView) {
    // Unknown targets are a defensive no-op — stay on the current (or
    // default) view rather than switching to an invalid state.
    if (!isKnownView(requestedView)) return isKnownView(currentView) ? currentView : DEFAULT_VIEW;
    return requestedView;
  }

  function viewVisibility(activeView) {
    const resolved = isKnownView(activeView) ? activeView : DEFAULT_VIEW;
    const visibility = {};
    for (const view of NAV_VIEWS) visibility[view] = view === resolved;
    return visibility;
  }

  return { NAV_VIEWS, DEFAULT_VIEW, isKnownView, resolveActiveView, viewVisibility };
});
```

- [ ] **Verify test passes**

Run: `node --test tests_js/nav-beh-1-view-switch-logic.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/nav-logic.js tests_js/nav-beh-1-view-switch-logic.test.js
git commit -m "feat(agent-ui): add pure view-switching decision logic for the nav rail"
```

---

### Task 3: Nav DOM wiring — click handlers, default-active, no-reload switch (BEH-1) [specialist: none]

**Charter capability:** App navigation shell
**Depends on:** Task 1, Task 2
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `static/js/nav.js`
- Test: `tests_js/nav-beh-1-wiring.test.js` (create)

- [ ] **Write failing test**

```javascript
// tests_js/nav-beh-1-wiring.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");

const src = readFileSync(require.resolve("../static/js/nav.js"), "utf8");

test("BEH-1: nav.js wires click listeners for all three nav ids", () => {
  for (const id of ["nav-incidents", "nav-escalations", "nav-directory"]) {
    assert.match(src, new RegExp(`getElementById\\("${id}"\\)`));
  }
  assert.match(src, /addEventListener\("click"/);
});

test("BEH-1: nav.js calls NavLogic's pure decision functions, never reimplements them", () => {
  assert.match(src, /NavLogic\.resolveActiveView/);
  assert.match(src, /NavLogic\.viewVisibility/);
});

test("BEH-1: showView toggles hidden and aria-current per the visibility map, no page reload", () => {
  assert.match(src, /\.hidden = /);
  assert.match(src, /setAttribute\("aria-current"/);
  assert.doesNotMatch(src, /location\.reload|location\.href\s*=/);
});

test("first activation dispatches to the corresponding screen loader", () => {
  assert.match(src, /loadEscalationsView\(/);
  assert.match(src, /loadDirectoryView\(/);
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/nav-beh-1-wiring.test.js`
Expected: FAIL — `static/js/nav.js` does not exist yet.

- [ ] **Implement**

```javascript
// static/js/nav.js
(function () {
  const loadedViews = new Set(["incidents"]); // Incidents is server-rendered on page load

  function showView(activeView) {
    const visibility = NavLogic.viewVisibility(activeView);
    for (const view of NavLogic.NAV_VIEWS) {
      const section = document.getElementById(`view-${view}`);
      if (section) section.hidden = !visibility[view];
      const navBtn = document.getElementById(`nav-${view}`);
      if (navBtn) {
        navBtn.classList.toggle("active", visibility[view]);
        if (visibility[view]) navBtn.setAttribute("aria-current", "page");
        else navBtn.removeAttribute("aria-current");
      }
    }
  }

  let currentView = NavLogic.DEFAULT_VIEW;

  function onNavClick(event) {
    const requestedView = event.currentTarget.dataset.view;
    currentView = NavLogic.resolveActiveView(requestedView, currentView);
    showView(currentView);
    if (currentView === "escalations" && !loadedViews.has("escalations")) {
      loadedViews.add("escalations");
      if (typeof loadEscalationsView === "function") loadEscalationsView();
    }
    if (currentView === "directory" && !loadedViews.has("directory")) {
      loadedViews.add("directory");
      if (typeof loadDirectoryView === "function") loadDirectoryView();
    }
  }

  for (const view of NavLogic.NAV_VIEWS) {
    const navBtn = document.getElementById(`nav-${view}`);
    if (navBtn) navBtn.addEventListener("click", onNavClick);
  }

  showView(currentView);
})();
```

- [ ] **Verify test passes**

Run: `node --test tests_js/nav-beh-1-wiring.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/nav.js tests_js/nav-beh-1-wiring.test.js
git commit -m "feat(agent-ui): wire nav rail click handlers to view-switching logic"
```

---

### Task 4: Nav rail / app-shell CSS [specialist: none]

**Charter capability:** App navigation shell
**Depends on:** Task 1, Task 3
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `static/css/nav.css`

- [ ] **Write failing test**

Extend `tests_js/nav-beh-1-markup.test.js` (Task 1) with:

```javascript
test("nav.css defines the nav-rail and app-shell layout rules", () => {
  const css = readFileSync(require.resolve("../static/css/nav.css"), "utf8");
  assert.match(css, /\.app-shell\s*\{/);
  assert.match(css, /\.nav-rail\s*\{/);
  assert.match(css, /\.nav-item\.active\s*\{/);
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/nav-beh-1-markup.test.js`
Expected: FAIL — `static/css/nav.css` does not exist yet.

- [ ] **Implement**

```css
/* static/css/nav.css */
.app-shell { display: flex; min-height: 100vh; }
.nav-rail {
  display: flex;
  flex-direction: column;
  width: 200px;
  flex-shrink: 0;
  border-right: 1px solid #ccc;
}
.nav-item {
  padding: 0.75rem 1rem;
  text-align: left;
  background: none;
  border: none;
  border-left: 3px solid transparent;
  cursor: pointer;
}
.nav-item.active { border-left-color: #2563eb; background: #eef2ff; font-weight: 600; }
.app-main { flex: 1; padding: 1rem; overflow: auto; }
.view[hidden] { display: none; }

#escalations-table, #users-table, #assignment-groups-table { width: 100%; border-collapse: collapse; }
#escalations-table td, #users-table td, #assignment-groups-table td { padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee; }
.owner-unassigned { color: #666; font-style: italic; }
[role="alert"] { background: #fee2e2; color: #991b1b; padding: 0.5rem 0.75rem; margin-bottom: 0.75rem; }
```

- [ ] **Verify test passes**

Run: `node --test tests_js/nav-beh-1-markup.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/css/nav.css tests_js/nav-beh-1-markup.test.js
git commit -m "feat(agent-ui): add nav rail and app-shell CSS"
```

---

### Task 5: Escalations view — fetch/render + edit-form `PATCH` wiring (BEH-2, BEH-3) [specialist: none]

**Charter capability:** Escalations screen
**Depends on:** Task 1
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `static/js/escalations-logic.js`, `static/js/escalations.js`
- Test: `tests_js/escalations-beh-2-render-logic.test.js`,
  `tests_js/escalations-beh-3-patch-payload.test.js` (create)

- [ ] **Write failing test**

```javascript
// tests_js/escalations-beh-2-render-logic.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { OWNER_UNASSIGNED_LABEL, displayOwner, escalationRowCells } =
  require("../static/js/escalations-logic.js");

test("BEH-2: owner: null renders as an explicit Unassigned state", () => {
  assert.equal(displayOwner(null), OWNER_UNASSIGNED_LABEL);
  assert.equal(displayOwner(undefined), OWNER_UNASSIGNED_LABEL);
  assert.equal(displayOwner("Rui Bastos"), "Rui Bastos");
});

test("BEH-2: row cells include number/account_id/summary/opened_at/closed_at/owner, never incident_number", () => {
  const cells = escalationRowCells({
    number: "ESCALATION-0001",
    incident_number: "INC0000123",
    account_id: "ACC-1",
    summary: "Renewal at risk",
    opened_at: "2026-01-01T00:00:00Z",
    closed_at: null,
    owner: null,
  });
  assert.equal(cells.number, "ESCALATION-0001");
  assert.equal(cells.account_id, "ACC-1");
  assert.equal(cells.summary, "Renewal at risk");
  assert.equal(cells.owner, "Unassigned");
  assert.equal(cells.ownerIsUnassigned, true);
  assert.equal("incident_number" in cells, false);
});

test("BEH-2: an owned, closed escalation renders its real values, not placeholders", () => {
  const cells = escalationRowCells({
    number: "ESCALATION-0002",
    account_id: "ACC-2",
    summary: "SLA dispute",
    opened_at: "2026-01-01T00:00:00Z",
    closed_at: "2026-02-01T00:00:00Z",
    owner: "Priya Nair",
  });
  assert.equal(cells.owner, "Priya Nair");
  assert.equal(cells.ownerIsUnassigned, false);
  assert.equal(cells.closed_at, "2026-02-01T00:00:00Z");
});
```

```javascript
// tests_js/escalations-beh-3-patch-payload.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { buildEscalationPatchPayload } = require("../static/js/escalations-logic.js");

const original = { summary: "Renewal at risk", owner: "Rui Bastos", closed_at: null };

test("BEH-3: only changed fields are sent", () => {
  const payload = buildEscalationPatchPayload(original, { summary: "Renewal at risk", owner: "Rui Bastos", closed_at: null });
  assert.deepEqual(payload, {});

  const payload2 = buildEscalationPatchPayload(original, { summary: "Escalated to VP", owner: "Rui Bastos", closed_at: null });
  assert.deepEqual(payload2, { summary: "Escalated to VP" });
});

test("BEH-3: explicitly blanking owner sends an explicit null, not an omission", () => {
  const payload = buildEscalationPatchPayload(original, { summary: "Renewal at risk", owner: "", closed_at: null });
  assert.deepEqual(payload, { owner: null });
});

test("BEH-3: setting closed_at sends the new value", () => {
  const payload = buildEscalationPatchPayload(original, { summary: "Renewal at risk", owner: "Rui Bastos", closed_at: "2026-03-01T00:00:00Z" });
  assert.deepEqual(payload, { closed_at: "2026-03-01T00:00:00Z" });
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/escalations-beh-2-render-logic.test.js tests_js/escalations-beh-3-patch-payload.test.js`
Expected: FAIL — `static/js/escalations-logic.js` does not exist yet.

- [ ] **Implement**

```javascript
// static/js/escalations-logic.js
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.EscalationsLogic = factory();
})(typeof window !== "undefined" ? window : globalThis, function () {
  const OWNER_UNASSIGNED_LABEL = "Unassigned";

  function displayOwner(owner) {
    return owner === null || owner === undefined ? OWNER_UNASSIGNED_LABEL : owner;
  }

  function escalationRowCells(escalation) {
    // incident_number is deliberately excluded — charter's escalations-screen scope.
    return {
      number: escalation.number,
      account_id: escalation.account_id,
      summary: escalation.summary,
      opened_at: escalation.opened_at,
      closed_at: escalation.closed_at,
      owner: displayOwner(escalation.owner),
      ownerIsUnassigned: escalation.owner === null || escalation.owner === undefined,
    };
  }

  function buildEscalationPatchPayload(original, edited) {
    const payload = {};
    if (edited.summary !== original.summary) payload.summary = edited.summary;
    if (edited.closed_at !== original.closed_at) payload.closed_at = edited.closed_at || null;
    const newOwner = edited.owner === "" ? null : edited.owner;
    if (newOwner !== original.owner) payload.owner = newOwner;
    return payload;
  }

  return { OWNER_UNASSIGNED_LABEL, displayOwner, escalationRowCells, buildEscalationPatchPayload };
});
```

```javascript
// static/js/escalations.js
let escalationsCache = [];

function renderEscalationsTable(escalations) {
  const tbody = document.querySelector("#escalations-table tbody");
  tbody.textContent = "";
  for (const escalation of escalations) {
    const cells = EscalationsLogic.escalationRowCells(escalation);
    const row = document.createElement("tr");
    row.dataset.number = cells.number;
    for (const key of ["number", "account_id", "summary", "opened_at", "closed_at"]) {
      const td = document.createElement("td");
      td.textContent = cells[key] || "";
      row.appendChild(td);
    }
    const ownerTd = document.createElement("td");
    ownerTd.textContent = cells.owner; // textContent only — never innerHTML
    if (cells.ownerIsUnassigned) ownerTd.classList.add("owner-unassigned");
    row.appendChild(ownerTd);
    row.addEventListener("click", () => openEscalationEditForm(escalation));
    tbody.appendChild(row);
  }
}

function openEscalationEditForm(escalation) {
  const form = document.getElementById("escalation-edit-form");
  form.hidden = false;
  form.elements.number.value = escalation.number;
  form.elements.summary.value = escalation.summary;
  form.elements.owner.value = escalation.owner || "";
  form.elements.closed_at.value = escalation.closed_at || "";
}

async function loadEscalationsView() {
  try {
    const resp = await fetch("/escalations");
    if (!resp.ok) throw { status: resp.status };
    const body = await resp.json();
    escalationsCache = body.items;
    renderEscalationsTable(escalationsCache);
  } catch (err) {
    showEscalationsError(UiErrors.formatApiError("Loading escalations", err));
  }
}

document.getElementById("escalation-edit-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  const number = form.elements.number.value;
  const original = escalationsCache.find((e) => e.number === number);
  const edited = {
    summary: form.elements.summary.value,
    owner: form.elements.owner.value,
    closed_at: form.elements.closed_at.value,
  };
  const payload = EscalationsLogic.buildEscalationPatchPayload(original, edited);
  try {
    const resp = await fetch(`/escalations/${encodeURIComponent(number)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw { status: resp.status };
    await loadEscalationsView();
    form.hidden = true;
  } catch (err) {
    showEscalationsError(
      err.status === 404
        ? UiErrors.escalationNotFoundMessage(number)
        : UiErrors.formatApiError("Saving escalation", err)
    );
  }
});

function showEscalationsError(message) {
  const el = document.getElementById("escalations-error");
  el.textContent = message;
  el.hidden = false;
}
```

- [ ] **Verify test passes**

Run: `node --test tests_js/escalations-beh-2-render-logic.test.js tests_js/escalations-beh-3-patch-payload.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/escalations-logic.js static/js/escalations.js \
  tests_js/escalations-beh-2-render-logic.test.js tests_js/escalations-beh-3-patch-payload.test.js
git commit -m "feat(agent-ui): add Escalations view fetch/render and PATCH edit wiring"
```

---

### Task 6: Directory view — fetch/render Users + AssignmentGroups (BEH-4) [specialist: none]

**Charter capability:** Directory screen
**Depends on:** Task 1
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `static/js/directory-logic.js`, `static/js/directory.js`
- Test: `tests_js/directory-beh-4-render-logic.test.js` (create)

- [ ] **Write failing test**

```javascript
// tests_js/directory-beh-4-render-logic.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { userRowCells, groupRowCells } = require("../static/js/directory-logic.js");

test("BEH-4: user row cells include name/role/assignment_group", () => {
  const cells = userRowCells({ name: "Rui Bastos", role: "Support Manager", assignment_group: null });
  assert.equal(cells.name, "Rui Bastos");
  assert.equal(cells.role, "Support Manager");
  assert.equal(cells.assignment_group, "");
});

test("BEH-4: a grouped user's assignment_group passes through unchanged", () => {
  const cells = userRowCells({ name: "Joao Pinto", role: "Support Engineer", assignment_group: "Support Tier 1" });
  assert.equal(cells.assignment_group, "Support Tier 1");
});

test("BEH-4: group row cells expose only name", () => {
  const cells = groupRowCells({ name: "Support Tier 1" });
  assert.deepEqual(cells, { name: "Support Tier 1" });
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/directory-beh-4-render-logic.test.js`
Expected: FAIL — `static/js/directory-logic.js` does not exist yet.

- [ ] **Implement**

```javascript
// static/js/directory-logic.js
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.DirectoryLogic = factory();
})(typeof window !== "undefined" ? window : globalThis, function () {
  function userRowCells(user) {
    return {
      name: user.name,
      role: user.role,
      assignment_group: user.assignment_group === null || user.assignment_group === undefined
        ? ""
        : user.assignment_group,
    };
  }

  function groupRowCells(group) {
    return { name: group.name };
  }

  return { userRowCells, groupRowCells };
});
```

```javascript
// static/js/directory.js
function renderTable(selector, rows, columns) {
  const tbody = document.querySelector(`${selector} tbody`);
  tbody.textContent = "";
  for (const row of rows) {
    const tr = document.createElement("tr");
    for (const key of columns) {
      const td = document.createElement("td");
      td.textContent = row[key]; // textContent only — never innerHTML
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

async function loadDirectoryView() {
  try {
    const [usersResp, groupsResp] = await Promise.all([fetch("/users"), fetch("/assignment_groups")]);
    if (!usersResp.ok) throw { status: usersResp.status, source: "users" };
    if (!groupsResp.ok) throw { status: groupsResp.status, source: "assignment_groups" };
    const usersBody = await usersResp.json();
    const groupsBody = await groupsResp.json();
    renderTable("#users-table", usersBody.items.map(DirectoryLogic.userRowCells), ["name", "role", "assignment_group"]);
    renderTable("#assignment-groups-table", groupsBody.items.map(DirectoryLogic.groupRowCells), ["name"]);
  } catch (err) {
    showDirectoryError(UiErrors.formatApiError(`Loading ${err.source || "directory"}`, err));
  }
}

function showDirectoryError(message) {
  const el = document.getElementById("directory-error");
  el.textContent = message;
  el.hidden = false;
}
```

- [ ] **Verify test passes**

Run: `node --test tests_js/directory-beh-4-render-logic.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/directory-logic.js static/js/directory.js tests_js/directory-beh-4-render-logic.test.js
git commit -m "feat(agent-ui): add Directory view fetch/render for Users and AssignmentGroups"
```

---

### Task 7: Shared error-message wiring across both screens (BEH-5, error cases) [specialist: none]

**Charter capability:** Escalations screen, Directory screen
**Depends on:** Task 5, Task 6
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `static/js/ui-errors.js`
- Test: `tests_js/beh-5-error-formatting.test.js` (create)

- [ ] **Write failing test**

```javascript
// tests_js/beh-5-error-formatting.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { formatApiError, escalationNotFoundMessage } = require("../static/js/ui-errors.js");

test("BEH-5: a network error (no status) names the failed action", () => {
  const msg = formatApiError("Loading escalations", {});
  assert.match(msg, /Loading escalations/);
  assert.match(msg, /network error/i);
});

test("BEH-5: a non-2xx response names the failed action and status, never a blank message", () => {
  const msg = formatApiError("Saving escalation", { status: 500 });
  assert.match(msg, /Saving escalation/);
  assert.match(msg, /500/);
});

test("Error Cases table: a 404 on PATCH /escalations/{number} names it as an escalation-not-found state", () => {
  const msg = escalationNotFoundMessage("ESCALATION-9999");
  assert.match(msg, /ESCALATION-9999/);
  assert.match(msg, /not found/i);
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/beh-5-error-formatting.test.js`
Expected: FAIL — `static/js/ui-errors.js` does not exist yet (it is referenced by
`escalations.js`/`directory.js` from Tasks 5-6 as `UiErrors`, but not yet defined, so this is also
the point where Tasks 5-6's browser-side error paths become exercisable, not just their happy
paths).

- [ ] **Implement**

```javascript
// static/js/ui-errors.js
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.UiErrors = factory();
})(typeof window !== "undefined" ? window : globalThis, function () {
  function formatApiError(action, error) {
    if (error && error.status) {
      return `${action} failed (HTTP ${error.status})`;
    }
    return `${action} failed: network error`;
  }

  function escalationNotFoundMessage(number) {
    return `Escalation ${number} not found`;
  }

  return { formatApiError, escalationNotFoundMessage };
});
```

Also update `static/index.html` (Task 1's file) to load `ui-errors.js` before `escalations.js`/
`directory.js` — already included in Task 1's `<script>` block above, so no further markup change
is needed here; this task only adds the file the existing `<script>` tag already points at.

- [ ] **Verify test passes**

Run: `node --test tests_js/beh-5-error-formatting.test.js`
Expected: PASS. Also re-run `node --test tests_js/escalations-beh-*.test.js tests_js/directory-beh-4-render-logic.test.js` to confirm no regression.

- [ ] **Commit**

```bash
git add static/js/ui-errors.js tests_js/beh-5-error-formatting.test.js
git commit -m "feat(agent-ui): add shared API-error formatting for Escalations and Directory views"
```

---

### Task 8: Static-assets pytest coverage + full regression pass [specialist: none]

**Charter capability:** App navigation shell, Escalations screen, Directory screen
**Depends on:** Tasks 1-7
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `tests/test_nav_static_assets.py`

- [ ] **Write failing test**

```python
# tests/test_nav_static_assets.py
from pathlib import Path

INDEX_HTML = Path("static/index.html")


def test_index_html_references_nav_rail_files():
    html = INDEX_HTML.read_text()
    assert '<link rel="stylesheet" href="/static/css/nav.css">' in html
    for script in (
        "ui-errors.js",
        "nav-logic.js",
        "nav.js",
        "escalations-logic.js",
        "escalations.js",
        "directory-logic.js",
        "directory.js",
    ):
        assert f'/static/js/{script}"' in html


def test_index_html_contains_nav_rail_and_three_view_containers():
    html = INDEX_HTML.read_text()
    assert '<nav class="nav-rail">' in html
    assert 'id="nav-incidents"' in html
    assert 'id="nav-escalations"' in html
    assert 'id="nav-directory"' in html
    assert 'id="view-incidents" class="view">' in html
    assert 'id="view-escalations" class="view" hidden>' in html
    assert 'id="view-directory" class="view" hidden>' in html


def test_nav_rail_css_and_js_files_exist():
    assert Path("static/css/nav.css").is_file()
    for script in (
        "ui-errors.js",
        "nav-logic.js",
        "nav.js",
        "escalations-logic.js",
        "escalations.js",
        "directory-logic.js",
        "directory.js",
    ):
        assert Path(f"static/js/{script}").is_file()
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_nav_static_assets.py`
Expected: PASS immediately if Tasks 1-7 already landed in this same plan run (this task exists to
give the *plan* an end-to-end pytest checkpoint, mirroring `user-directory.plan.md`'s Task 3
pattern of a verification-only task) — if any assertion fails, it means an earlier task's file or
markup is missing/misnamed, and this task's own code-change budget covers exactly and only fixing
that gap, not adding new behavior.

- [ ] **Implement**

No new production code expected (see above). If a gap surfaced above, fix it in the specific
Task 1-7 file it belongs to and re-run.

- [ ] **Verify test passes**

Run the full gate suite:

```bash
python3 -m pytest -q
ruff check .
node --test tests_js/**/*.test.js
```

Expected: all green — every existing itsm-api test (`tests/test_escalations.py`,
`tests/test_directory.py`, etc.) still passes unmodified, plus this plan's new
`tests/test_nav_static_assets.py` and every `tests_js/*.test.js` file from Tasks 1-7.

- [ ] **Commit**

```bash
git add tests/test_nav_static_assets.py
git commit -m "test(agent-ui): add static-assets regression coverage for nav rail and new views"
```

---

## Quality Gates

- Test Suite: `python3 -m pytest -q` (required — per `.context-index/governance/gates.yaml`'s
  `test` gate)
- Linter: `ruff check .` (required — per `governance/gates.yaml`'s `lint` gate)
- JS Unit Tests: `node --test tests_js/**/*.test.js` (required by this plan; not yet a separate
  entry in `governance/gates.yaml` — first plan in this repo to introduce `tests_js/`, matching
  `mock-jira`'s `kanban-ui` plans' equivalent gate, which is likewise plan-documented rather than
  `gates.yaml`-wired there)
- Real-browser end-to-end coverage of this spec's BEH-1 through BEH-5 is `ui-e2e.spec.md`'s scope
  (a separate, already-reviewed Live Spec with its own plan) — out of scope for this plan
- All acceptance criteria from `escalations-directory-nav.spec.md` satisfied:
  - [ ] Nav shell shows exactly one view at a time, Incidents active by default (BEH-1)
  - [ ] Escalations view renders every row including ownerless ones explicitly (BEH-2)
  - [ ] Escalation edit form saves changed fields, including explicit-null owner (BEH-3)
  - [ ] Directory view renders Users and AssignmentGroups read-only (BEH-4)
  - [ ] Every API failure surfaces a visible, specific message (BEH-5)
  - [ ] All quality gates pass (tests, lint)
  - [ ] No constitutional violations introduced
