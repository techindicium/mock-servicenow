<!-- partial_schema: plan@1 -->

# Implementation Plan: Incident console (list, record view, work notes, SLA, editing, create)

> **Methodology:** adev
> **Charter:** .context-index/specs/features/agent-ui/charter.md
> **Spec:** .context-index/specs/features/agent-ui/incident-console.spec.md
> **Review:** PASS (2026-09-07, revision 2)
> **Platform:** FastAPI (Python 3.11) backend, already implemented; static HTML/CSS/vanilla JS
> frontend with zero build step, served same-origin by that same FastAPI process; Node.js
> built-in test runner (`node --test`, no npm dependencies) for JS unit tests.

**Goal:** Ship the incident console — a filterable, paginated list view and a record (detail)
view with work-note timeline, SLA panel, unguarded field editing, and incident creation — as
static assets served directly by `itsm-api`'s own FastAPI process. This plan is the **agent-ui
module's foundation plan**: it builds the page skeleton, shared fetch/render helpers, and every
behavior in `incident-console.spec.md` (BEH-1 through BEH-9), but per the spec's own Task Map it
does **not** build the left-hand nav rail or cross-view (Incidents/Escalations/Directory)
switching logic — that is `escalations-directory-nav.spec.md`'s plan, which extends the files
this plan creates.

**Architecture:** `app/main.py` mounts a new `static/` directory via `StaticFiles` and repurposes
`GET /` to serve `static/index.html` via `FileResponse` (see Design decision below on why this is
safe). The page loads two vanilla-JS files, mirroring `mock-jira`'s `kanban-ui` split exactly:
`incident-logic.js`, a dependency-free, UMD-lite module of pure functions (null-field formatting,
filter query-param building, pagination shaping, work-note sort/shaping, SLA breach-flagging,
form validation, a PATCH-diffing helper, and BEH-9's error-message formatting), and
`incident.js`, a thin DOM/fetch imperative shell that calls the same-origin `/incidents`,
`/incidents/{number}/work_notes`, and `/sla` endpoints and wires pure-function results into the
DOM using `createElement`/`textContent` — never `innerHTML` string interpolation of API-returned
text — satisfying the spec's Postconditions safe-rendering requirement directly rather than via
an `escapeHtml`-before-`innerHTML` pattern. Pure logic is unit-tested with Node's built-in test
runner (`node:test` + `node:assert/strict`); the static-serving wiring is unit-tested with the
existing pytest + `TestClient` fixture already used for the API (`tests/conftest.py::client`).
`incident.js` itself is not separately unit-tested — this repo's `governance/validate.yaml`
disables subagent visual/browser-review checks, and the sibling `ui-e2e` plan (deferred capability
in the charter, v1.1 milestone) owns real-browser coverage of the wired-up shell.

**Constitution Validation (Step 3):** Checked every task's files/behavior against `Architecture
Boundaries`. No task adds a permission check, confirmation dialog, or state-transition guard to
the edit-incident or add-work-note flows (Task 6 is the task that would be tempted to add one to
BEH-7's resolve-with-open-breach case, and its entire point — mirroring
`incident-tools.plan.md` Task 5's MCP-layer proof — is that no such guard exists in
`diffIncidentFields` or the PATCH submit handler). No task touches auth, adds a dependency on
another repo, or changes an itsm-api endpoint's request/response shape (this plan only reads
`app/routers/*.py` and `app/models.py`, never modifies them). `app/main.py`'s repurposing of
`GET /` from a JSON health body to an HTML shell is an additive/internal change to a route no
spec's Behavioral Contract asserts a JSON shape for (see Design decision below), so it needs no
human approval under "breaking changes to the public HTTP API contract" — the itsm-api specs'
own behavioral contracts never mention `GET /` at all. No task is marked `[REQUIRES HUMAN
APPROVAL]`.

**Design decision — repurposing `GET /` from JSON health check to the UI shell is safe:**
`app/main.py`'s current `GET /` returns `{"status": "ok", "service": "mock-servicenow"}` with a
comment explaining it exists so `tests_e2e/servers.py::start_itsm_api()` can poll for a healthy
process. That fixture's poll (`resp = httpx.get(base_url + "/", timeout=1); if resp.status_code
== 200`) only ever checks the status code, never the response body or `content-type` — an HTML
200 satisfies it identically to a JSON 200. `grep`-confirmed: no test anywhere in `tests/` or
`tests_e2e/` asserts `/`'s JSON body (`tests/test_gates_config.py`, `test_pytest_config.py`,
`test_requirements_files.py` assert unrelated things; no `test_main.py`/`test_health.py` exists).
PRD.md's Acceptance criteria and the agent-ui charter's Business Intent both require the UI at
`/`, and no itsm-api Live Spec's Behavioral Contract mentions `GET /`'s shape — it is
charter-wide infrastructure, not a tested behavior, so repurposing it is squarely "internal
refactor that doesn't change the HTTP surface" other tracks depend on (they depend on
`/incidents`, `/sla`, etc., never `/`). Task 1 keeps the poll-friendly 200 status; the JSON health
body is dropped, not moved elsewhere, since nothing consumes it.

**Design decision — safe rendering is DOM-API-first, not `escapeHtml`-before-`innerHTML`:** The
spec's Postconditions require every user-supplied free-text field (`short_description`,
`description`, work-note `created_by`/`body`) to be "inserted as text (via `textContent`/safe DOM
APIs), never interpreted as HTML or script." `mock-jira`'s `board-logic.js` satisfies an
equivalent requirement with `escapeHtml()` called before string-concatenated `innerHTML`
assignment — also safe, but one extra manual step away from a bug (forgetting to escape one
field). This plan instead has `incident-logic.js`'s render-shaping functions return **plain data**
(arrays of `{label, value}` pairs, row objects, etc.), and `incident.js` builds every DOM node via
`document.createElement(...)` + `.textContent = value`, never `innerHTML`, for any node that could
carry user-supplied text. This is a stricter, harder-to-regress reading of the same Postcondition,
and is why `incident-logic.js` has no `escapeHtml`/`buildXHtml`-string-returning function anywhere
in this plan, unlike `board-logic.js`'s `buildCardHtml`.

**Design decision — `category` is a free-text filter/field, not a fixed-enum `<select>`:**
Reading `app/models.py`'s `IncidentCreate`/`IncidentPatch` and `app/routers/incidents.py` confirms
`category` is an unconstrained `str` at the API layer — no `Literal` enum exists for it (unlike
`state` five-value and `priority` 1-4 literal enums, which this plan does render as `<select>`
populated from `incident-logic.js`'s exported `INCIDENT_STATES`/`PRIORITIES` constants, satisfying
the charter's "select controls populated from the same fixed enums the API validates against"
invariant for the fields that actually have one). `category` and `account_id` render as free-text
`<input>` filters/fields in both the list-filter form and the create-incident form; no task
invents a `category` enum the API itself doesn't enforce.

**Design decision — the nav-rail mount point is an empty, labeled `<nav>` inside an `.app-shell`
wrapper:** Mirroring `mock-jira/static/index.html`'s current (post-`board-view` evolution)
`.app-shell` > `.sidebar` + `.app-main` structure, Task 1's `index.html` wraps the page in
`<div class="app-shell">` containing `<nav id="nav-rail" class="sidebar" aria-label="Main
navigation"></nav>` (empty — no `<button class="nav-item">` markup, no `data-view` attributes, no
`click` listeners) immediately followed by `<div class="app-main"><section id="view-incidents"
class="view">...</section></div>` holding this spec's entire list/record/create UI. `#view-incidents`
is never `hidden` by this plan (there is only one top-level view until the sibling plan adds
Escalations/Directory), so the console is immediately visible and usable standalone, with or
without the nav rail ever being populated. `console.css` gives `.sidebar` a fixed width and
`.app-main` `flex: 1` so the layout doesn't visibly shift when the sibling plan later drops
`.nav-item` buttons into `#nav-rail` — this plan's CSS classes (`.app-shell`, `.sidebar`,
`.app-main`, `.view`) are deliberately the same class names `kanban-ui` already proved out, so the
sibling plan can reuse them verbatim instead of inventing its own. This is a judgment call, not a
spec requirement: the alternative (no `<nav>` element at all, letting the sibling plan insert one)
was rejected because it would force that plan to also rewrite `index.html`'s top-level layout
wrapper instead of just populating an existing, empty element — a smaller, safer diff for a
sibling plan authored independently against this one.

**Design decision — `diffIncidentFields` is a pure change-detector, never a validity check:**
BEH-7 requires the PATCH to carry "exactly the changed fields" with "no client-side check blocking
or flagging the save," including a resolve-with-open-breach transition. `incident-logic.js`'s
`diffIncidentFields(original, edited)` (built in Task 6) compares each of the four patchable
fields and returns only the ones that differ — it has no branch that inspects `state`'s new value,
looks at SLA data, or refuses to include a change. Task 6's failing-test-first step includes a
dedicated regression test asserting a `resolved`-with-`has_breached:true` transition diffs and
submits identically to any other state change, the same "prove the absence of a guard" pattern
`mcp-server/incident-tools.plan.md` Task 5 already established for the MCP layer this UI sits
beside.

---

## File Structure

**Create:**
- `static/index.html` — page shell: `.app-shell` > empty `#nav-rail` `<nav>` mount point (see
  Design decision) + `.app-main` > `#view-incidents` containing the list sub-view (filter form,
  paginated table, pagination controls, "New Incident" entry point), the create-incident form,
  and the record sub-view (field list, edit form, SLA panel, work-note timeline + add-note form),
  plus a top-level error banner. No `.nav-item` markup, no `data-view` attributes.
- `static/css/console.css` — shared layout/typography (`.app-shell`, `.sidebar`, `.app-main`,
  `.view`, form/table basics) plus incident-console-specific styling (`.sla-breached` breach
  highlighting, null-field muted styling).
- `static/js/incident-logic.js` — pure, dependency-free logic module (UMD-lite: browser global
  `IncidentLogic` + Node `require()`). Built up incrementally across Tasks 1-7.
- `static/js/incident.js` — thin DOM/fetch imperative shell wiring `incident-logic.js` functions
  to the page. Built up incrementally across Tasks 1-7.
- `tests/test_static_assets.py` — pytest: verifies the FastAPI process serves the console shell
  and static assets, mirroring mock-jira's file of the same name.
- `tests_js/beh-9-error-formatting.test.js` — Node `node:test`: fetch/HTTP error-message
  formatting (created here since Task 1 builds the shared fetch wrapper; extended by Tasks 3, 6,
  7 for entity-specific 404/422 cases).
- `tests_js/beh-1-list-load.test.js` — Node `node:test`: default (unfiltered) list load +
  pagination shaping.
- `tests_js/beh-2-list-filters.test.js` — Node `node:test`: filter query-param building and
  full-replace-never-merge semantics.
- `tests_js/beh-3-record-view.test.js` — Node `node:test`: record field shaping, explicit
  null-field formatting.
- `tests_js/beh-4-work-note-timeline.test.js` — Node `node:test`: chronological sort + row
  shaping.
- `tests_js/beh-5-add-work-note.test.js` — Node `node:test`: add-work-note form validation and
  timeline-append shaping.
- `tests_js/beh-6-sla-panel.test.js` — Node `node:test`: SLA row breach-flagging (data shaping,
  never blocking).
- `tests_js/beh-7-edit-incident.test.js` — Node `node:test`: `diffIncidentFields`, including the
  resolve-with-open-breach no-guard regression test.
- `tests_js/beh-8-create-incident.test.js` — Node `node:test`: create-incident six-field
  validation.

**Modify:**
- `app/main.py` — mount `static/` via `StaticFiles`; change `GET /` to serve `static/index.html`
  via `FileResponse` instead of the current JSON health body (Task 1; see Design decision above).
- `.context-index/governance/gates.yaml` — add a `test-js` gate (Task 1, alongside the first JS
  test file it protects), mirroring `mock-jira`'s exact gate shape.

**Reference (read, do not modify):**
- `.context-index/specs/features/itsm-api/incident-lifecycle.spec.md`,
  `work-notes.spec.md`, `sla-records.spec.md` — the sole behavioral source of truth for every
  request/response shape and error body this UI renders and posts.
- `app/routers/incidents.py`, `app/routers/work_notes.py`, `app/routers/sla.py` — exact query
  parameter names, response envelopes (`IncidentPage`/`WorkNoteListResponse`/`PaginatedTaskSla`:
  `items`/`page`/`page_size`/`total`), and `_PATCHABLE_FIELDS` (`state`, `priority`,
  `assigned_to`, `assignment_group`).
- `app/models.py` — `INCIDENT_STATES` (`new`, `in_progress`, `on_hold`, `resolved`, `closed`),
  `NOTE_TYPES` (`comment`, `work_note`, `state_change`, `proposal_sent`), `priority` (`1`-`4`
  literal), and confirmation that `category` carries no fixed enum.
- `app/errors.py` — the `{"message": ..., "code": ...}` error-body shape every non-2xx response
  carries, read verbatim by this UI's error banners.
- `tests/conftest.py` — existing `client` fixture (`TestClient(create_app(tmp_path/"test.db"))`)
  and `conn` fixture — reuse this fixture, do not create a second one.
- `tests_e2e/servers.py` — confirms `start_itsm_api()`'s poll of `GET /` checks only status code,
  never body shape (basis for the Design decision above).
- `/Users/dpavancini/Development/adev-course/mock-jira/.context-index/specs/features/kanban-ui/board-view.plan.md`
  — architecture/file-layout pattern this plan mirrors (pure-logic-module + thin-DOM-shell split,
  Node's built-in test runner, the `test-js` gate addition).
- `/Users/dpavancini/Development/adev-course/mock-jira/static/js/board-logic.js`, `board.js`,
  `static/index.html`, `static/css/board.css` — code-style exemplars (UMD-lite module, `fetchJson`
  wrapper with error normalization, `formatFetchError`, `.app-shell`/`.sidebar`/`.app-main`
  layout, `diffIssueFields`-style pure diffing helper).
- `.context-index/specs/features/agent-ui/charter.md` — Capability Map, Domain Model invariants
  (fixed-enum selects, null-field explicitness).
- `.context-index/specs/features/mcp-server/incident-tools.plan.md` Task 5 — the sibling
  "prove no guard exists" pattern this plan's Task 6 mirrors at the UI layer.
- `CLAUDE.md` — constitution: Principle 4 (HTTP contract is the boundary), Principle 5 (no write
  guards), Principle 6 (seeded discrepancies are load-bearing).
- `.context-index/governance/gates.yaml` — existing `test`/`lint`/`integration-test`/`e2e-smoke`
  gate shape.

---

## Context Packets

> No `source-manifest.files[]` exists on this spec yet (first implementation pass). Context
> packets fall back to charter + spec + the three itsm-api specs (as the HTTP contract) + the
> `mock-jira` exemplar files, per the standard "no source-manifest" fallback path.

### Task 1 Context
- Spec: Preconditions (same-origin, no base-URL config), Task Map row 1 ("Static shell... no
  nav-item markup or view-switching logic"), Error Cases table, BEH-9 (error-message shape)
- Charter: Business Intent (served same-origin by itsm-api), Scope's nav-rail note
- Source (full read): `app/main.py`, `tests/conftest.py`, `tests_e2e/servers.py`
- Exemplar (full read): `mock-jira/static/index.html`, `mock-jira/static/css/board.css`,
  `mock-jira/.context-index/specs/features/kanban-ui/board-view.plan.md` Task 1 and Task 3
  (fetch wrapper + gate addition)

### Task 2 Context
- Spec: BEH-1, BEH-2, Postconditions ("never leaves a previous filter's data visibly mixed")
- Charter: Capability "Incident list view"; Domain Model `IncidentListFilter` entity
- Source: `app/routers/incidents.py` `list_incidents` (query params, `IncidentPage` shape —
  signature-level read; full read of the function already done in Step 3)

### Task 3 Context
- Spec: BEH-3, BEH-4, Postconditions (null-field explicitness, "no stale render survives")
- Charter: Domain Model invariant ("every null field shown as an explicit empty/unassigned state")
- Source: `app/routers/incidents.py` `get_incident` (404 body), `app/routers/work_notes.py`
  `list_work_notes` (chronological order already server-side; UI sorts defensively)

### Task 4 Context
- Spec: BEH-5, Preconditions ("`created_by` is free-text, never a picker")
- Charter: Capability "Work-note timeline + add form"
- Source: `app/routers/work_notes.py` `create_work_note` (required fields, 201 shape, 404 row)

### Task 5 Context
- Spec: BEH-6, System Constitution Reference Principle 6
- Charter: Capability "SLA panel"; Scope's "no annotation claiming a breach is wrong" note
- Source: `app/routers/sla.py` `list_sla_records` (`incident_number` filter, `TaskSlaRead` shape)

### Task 6 Context
- Spec: BEH-7, Postconditions ("no client-side check accepts/rejects what the API wouldn't"),
  System Constitution Reference Principle 5
- Charter: Scope's unguarded-editing note; constitution Non-Negotiable Principle 5
- Source: `app/routers/incidents.py` `patch_incident` (`_PATCHABLE_FIELDS`, no guard, 404 row)

### Task 7 Context
- Spec: BEH-8
- Charter: Capability "Create incident"
- Source: `app/routers/incidents.py` `create_incident` (six required fields, defaults, 422 row)

---

## Parallelization

- Group A (sequential): Task 1 → Task 2 → Task 3 → Task 4 → Task 5 → Task 6 → Task 7

Every task after Task 1 extends both shared frontend files (`static/js/incident-logic.js`,
`static/js/incident.js`) and, for Tasks 3-7, the same `#incident-record-view` region of
`static/index.html`. There is no file-disjoint pair of tasks in this plan — the same serialization
rationale `board-view.plan.md` documents applies here identically.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Static shell + shared fetch/render helpers | medium | unit | — | 4 create, 2 modify |
| 2 | Incident list view | medium | unit | Task 1 | 1 create, 2 modify |
| 3 | Incident record view (fields + work-note timeline render) | medium | unit | Task 2 | 2 create, 3 modify |
| 4 | Add work note | small | unit | Task 3 | 1 create, 2 modify |
| 5 | SLA panel | small | unit | Task 3 | 1 create, 3 modify |
| 6 | Edit incident fields [Confirm no guard exists] | medium | unit | Task 3 | 1 create, 3 modify |
| 7 | Create incident | small | unit | Task 2, Task 6 | 1 create, 3 modify |

All tasks resolve to the `unit` strategy (source: fallback — no `test_strategy` in spec
frontmatter, no `test_strategies` entries in `manifest.yaml` matching `static/**`/`tests_js/**`
paths; auto-detection finds no migration/IaC/schema/contract/visual signal — `visual` specifically
requires a `react`/`vue`/`svelte`/`angular` package, which this project deliberately does not
have). Strategy Summary and Test Infrastructure Requirements sections are both omitted per plan
template rules (all-unit, no `infra_requirements:` declared).

**Granularity:** `per-behavior` (source: manifest — `test_policy.granularity: per-behavior`).
Each spec behavior (BEH-1 through BEH-9) gets one canonical suite file under `tests_js/`; a task
"creates" the suite the first time that behavior is implemented and "extends" it on a later task
touching the same behavior. `tests_js/beh-9-error-formatting.test.js` is created by Task 1 and
extended by Tasks 3, 6, and 7 (entity-specific 404/422 message cases). `tests/test_static_assets.py`
is foundational/infra rather than behavior logic, per the same "no source-manifest" fallback path
`board-view.plan.md` used for its own equivalent file.

---

## Task Structure

### Task 1: Static shell + shared fetch/render helpers [specialist: none]

**Charter capability:** Incident list view / Incident record view (scaffold)
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `static/index.html`
- Create: `static/css/console.css`
- Create: `tests/test_static_assets.py`
- Create: `tests_js/beh-9-error-formatting.test.js`
- Modify: `app/main.py` (mount `static/`, repurpose `GET /`)
- Modify: `.context-index/governance/gates.yaml` (add `test-js` gate)

**Tests:** `tests/test_static_assets.py` (new — foundational); `tests_js/beh-9-error-formatting.test.js` (new — BEH-9 core formatter)

**Context to load:**
- `app/main.py` (full read), `tests/conftest.py` (`client` fixture)
- `mock-jira/static/index.html`, `static/css/board.css` (layout exemplar)

- [ ] **Write failing test**

```python
# tests/test_static_assets.py
def test_root_serves_incident_console_shell(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert 'id="nav-rail"' in body
    assert 'id="view-incidents"' in body
    assert 'id="incidents-table-body"' in body
    assert 'id="incident-record-view"' in body
    assert 'id="create-incident-form"' in body
    # This plan explicitly does not build nav-item markup — the sibling
    # escalations-directory-nav plan owns that (see incident-console.spec.md Task Map).
    assert "nav-item" not in body


def test_static_css_is_served(client):
    resp = client.get("/static/css/console.css")
    assert resp.status_code == 200


def test_static_js_is_served(client):
    resp = client.get("/static/js/incident-logic.js")
    assert resp.status_code == 200
    resp = client.get("/static/js/incident.js")
    assert resp.status_code == 200
```

```javascript
// tests_js/beh-9-error-formatting.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { formatFetchError } = require("../static/js/incident-logic.js");

test("BEH-9: names the failed action and the server message on an HTTP error", () => {
  const msg = formatFetchError("Loading incidents", { status: 500, message: "boom" });
  assert.match(msg, /Loading incidents/);
  assert.match(msg, /500/);
  assert.match(msg, /boom/);
});

test("BEH-9: falls back to a network-error message with no status", () => {
  const msg = formatFetchError("Loading incidents", { message: "Failed to fetch" });
  assert.match(msg, /Loading incidents/);
  assert.match(msg, /Failed to fetch/);
});

test("BEH-9: never returns an empty message even with a bare error", () => {
  const msg = formatFetchError("Loading incidents", {});
  assert.ok(msg && msg.length > 0);
});

test("BEH-9: a 422 message surfaces the API's own field-naming text verbatim", () => {
  const msg = formatFetchError("Saving incident", {
    status: 422, message: "state must be one of: new, in_progress, on_hold, resolved, closed",
  });
  assert.match(msg, /state must be one of/);
});
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q -- tests/test_static_assets.py`
Expected: FAIL — `404` on `GET /` (still the old JSON health route) and `404`/connection error on
the static paths (no `static/` mount yet).

Run: `node --test tests_js/beh-9-error-formatting.test.js`
Expected: FAIL — `Cannot find module '../static/js/incident-logic.js'`

- [ ] **Implement**

`static/js/incident-logic.js` (initial slice — grows in every later task):

```javascript
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.IncidentLogic = factory();
  }
})(typeof window !== "undefined" ? window : globalThis, function () {
  const INCIDENT_STATES = ["new", "in_progress", "on_hold", "resolved", "closed"];
  const PRIORITIES = [1, 2, 3, 4];
  const NOTE_TYPES = ["comment", "work_note", "state_change", "proposal_sent"];

  function formatFetchError(action, error) {
    if (error && error.status) {
      return `${action} failed (HTTP ${error.status}): ${error.message || "unexpected error"}`;
    }
    return `${action} failed: ${(error && error.message) || "network error"}`;
  }

  return { INCIDENT_STATES, PRIORITIES, NOTE_TYPES, formatFetchError };
});
```

`static/js/incident.js` (fetch + error-banner helpers only — no page wiring yet):

```javascript
(function () {
  async function fetchJson(url, options) {
    let resp;
    try {
      resp = await fetch(url, options);
    } catch (networkErr) {
      throw { message: networkErr.message };
    }
    if (!resp.ok) {
      let body = null;
      try {
        body = await resp.json();
      } catch (_parseErr) {
        // non-JSON error body — body stays null, message falls back below
      }
      throw { status: resp.status, message: body && body.message };
    }
    return resp.status === 204 ? null : resp.json();
  }

  function showError(message) {
    const banner = document.getElementById("incidents-error");
    banner.textContent = message;
    banner.hidden = false;
  }

  function clearError() {
    document.getElementById("incidents-error").hidden = true;
  }

  window.IncidentApp = { fetchJson, showError, clearError };
})();
```

`static/index.html` (full skeleton — sub-sections referenced by id are filled in by later tasks;
Task 1 creates every id up front so `test_root_serves_incident_console_shell` can assert against
the complete shape once, rather than each task adding assertions piecemeal):

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>mock-servicenow Incident Console</title>
  <link rel="stylesheet" href="/static/css/console.css" />
  <script src="/static/js/incident-logic.js"></script>
  <script src="/static/js/incident.js" defer></script>
</head>
<body>
  <div class="app-shell">
    <!-- Intentionally empty. escalations-directory-nav.plan.md (sibling spec's plan)
         populates this with Incidents/Escalations/Directory nav-item buttons and the
         top-level view-switching logic. This plan owns only #view-incidents below. -->
    <nav id="nav-rail" class="sidebar" aria-label="Main navigation"></nav>

    <div class="app-main">
      <section id="view-incidents" class="view">
        <h1>Incidents</h1>
        <div id="incidents-error" role="alert" hidden></div>

        <section id="incident-list-view">
          <form id="incident-filter-form">
            <label>State
              <select id="filter-state" name="state"><option value="">All</option></select>
            </label>
            <label>Category <input id="filter-category" name="category" /></label>
            <label>Account <input id="filter-account_id" name="account_id" /></label>
            <label>Escalated
              <select id="filter-escalated" name="escalated">
                <option value="">All</option>
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            </label>
            <button type="submit">Apply filters</button>
          </form>

          <button id="open-create-incident" type="button">New Incident</button>

          <table id="incidents-table">
            <thead>
              <tr>
                <th>Number</th><th>Short description</th><th>State</th><th>Priority</th>
                <th>Category</th><th>Account</th><th>Escalated</th>
              </tr>
            </thead>
            <tbody id="incidents-table-body"></tbody>
          </table>

          <div id="incidents-pagination">
            <button id="incidents-prev-page" type="button">Previous</button>
            <span id="incidents-page-info"></span>
            <button id="incidents-next-page" type="button">Next</button>
          </div>
        </section>

        <section id="create-incident" hidden>
          <h2>New Incident</h2>
          <form id="create-incident-form">
            <label>Account ID <input id="create-account_id" name="account_id" required /></label>
            <label>Category <input id="create-category" name="category" required /></label>
            <label>Short description
              <input id="create-short_description" name="short_description" required />
            </label>
            <label>Description
              <textarea id="create-description" name="description" required></textarea>
            </label>
            <label>State <select id="create-state" name="state" required></select></label>
            <label>Priority <select id="create-priority" name="priority" required></select></label>
            <button type="submit">Create Incident</button>
            <button id="cancel-create-incident" type="button">Cancel</button>
            <p id="create-incident-error" role="alert" hidden></p>
          </form>
        </section>

        <section id="incident-record-view" hidden>
          <button id="back-to-list" type="button">Back to list</button>
          <h2 id="record-number"></h2>
          <dl id="record-fields"></dl>

          <form id="edit-incident-form">
            <label>State <select id="edit-state" name="state"></select></label>
            <label>Priority <select id="edit-priority" name="priority"></select></label>
            <label>Assigned to <input id="edit-assigned_to" name="assigned_to" /></label>
            <label>Assignment group <input id="edit-assignment_group" name="assignment_group" /></label>
            <button type="submit">Save changes</button>
            <p id="edit-incident-error" role="alert" hidden></p>
          </form>

          <section id="sla-panel">
            <h3>SLA</h3>
            <table id="sla-table">
              <thead>
                <tr>
                  <th>Definition</th><th>Target (min)</th><th>Actual (min)</th>
                  <th>Breached</th><th>Business hours only</th>
                </tr>
              </thead>
              <tbody id="sla-table-body"></tbody>
            </table>
          </section>

          <section id="work-notes-panel">
            <h3>Work notes</h3>
            <ol id="work-notes-timeline"></ol>

            <form id="add-work-note-form">
              <label>Created by <input id="note-created_by" name="created_by" required /></label>
              <label>Type <select id="note-note_type" name="note_type" required></select></label>
              <label>Body <textarea id="note-body" name="body" required></textarea></label>
              <button type="submit">Add work note</button>
              <p id="add-work-note-error" role="alert" hidden></p>
            </form>
          </section>
        </section>
      </section>
    </div>
  </div>
</body>
</html>
```

`static/css/console.css`: `.app-shell` flex row (`.sidebar` fixed-width, `.app-main` `flex: 1`),
`[hidden] { display: none !important; }`, basic table/form styling, and one incident-specific
rule reserved for Task 5: `.sla-breached { /* visibly distinct, not alarming */ }` (filled in by
Task 5's Implement step — declared as a placeholder comment here so `console.css`'s structure is
stable from Task 1 onward).

`app/main.py`:

```python
from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(db_path: str) -> FastAPI:
    app = FastAPI(title="mock-servicenow itsm-api")
    conn = get_connection(db_path)
    create_schema(conn)
    app.state.db_conn = conn

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(incidents_router)
    app.include_router(work_notes_router)
    app.include_router(sla_router)
    app.include_router(directory_router)
    app.include_router(escalations_router)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def serve_incident_console() -> FileResponse:
        # Repurposed from a JSON health body ({"status": "ok", ...}) to the agent-ui shell, per
        # incident-console.plan.md's Design decision: PRD.md and the agent-ui charter require
        # the UI at "/", and tests_e2e/servers.py's start_itsm_api() fixture polls this route for
        # a 200 status only — never the JSON body — so this change keeps that poll working
        # unchanged. `include_in_schema=False` keeps this out of the OpenAPI schema, matching
        # the prior health route's intent.
        return FileResponse(str(STATIC_DIR / "index.html"))

    return app
```

`.context-index/governance/gates.yaml`: add a new gate alongside `test`/`lint`:

```yaml
  - id: test-js
    name: JS Unit Tests
    kind: deterministic
    tier: fast
    command: [node, --test, tests_js/]
    scope: project
    required: true
    severity: error
    triggers:
      - post-task
      - post-implement
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q -- tests/test_static_assets.py`
Expected: PASS

Run: `node --test tests_js/beh-9-error-formatting.test.js`
Expected: PASS

- [ ] **Commit**

Branch (if not already created): `feat/agent-ui/incident-console`

```bash
git add static/index.html static/css/console.css static/js/incident-logic.js \
  static/js/incident.js app/main.py tests/test_static_assets.py \
  tests_js/beh-9-error-formatting.test.js .context-index/governance/gates.yaml
git commit -m "feat(agent-ui): serve incident console shell as static assets from itsm-api"
```

---

### Task 2: Incident list view [specialist: none]

**Charter capability:** Incident list view
**Depends on:** Task 1
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `tests_js/beh-1-list-load.test.js`, `tests_js/beh-2-list-filters.test.js`
- Modify: `static/js/incident-logic.js` (add `buildIncidentQueryParams`, `shapePaginationInfo`)
- Modify: `static/js/incident.js` (add list load/render, filter submit, pagination wiring)

**Tests:** `tests_js/beh-1-list-load.test.js` (new — BEH-1); `tests_js/beh-2-list-filters.test.js`
(new — BEH-2)

**Context to load:**
- Spec BEH-1, BEH-2, Postconditions
- `app/routers/incidents.py` `list_incidents` (query params, `IncidentPage` shape)

- [ ] **Write failing test**

```javascript
// tests_js/beh-1-list-load.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { buildIncidentQueryParams, shapePaginationInfo } = require("../static/js/incident-logic.js");

test("BEH-1: no filters and no page produces an empty query-param object", () => {
  assert.deepEqual(buildIncidentQueryParams({}, undefined, undefined), {});
});

test("BEH-1: pagination shape reflects page/page_size/total from the API response", () => {
  const info = shapePaginationInfo(1, 50, 120);
  assert.equal(info.page, 1);
  assert.equal(info.totalPages, 3);
  assert.equal(info.hasPrev, false);
  assert.equal(info.hasNext, true);
});

test("BEH-1: a single, exact-page-size total has no next page", () => {
  const info = shapePaginationInfo(1, 50, 50);
  assert.equal(info.hasNext, false);
});
```

```javascript
// tests_js/beh-2-list-filters.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { buildIncidentQueryParams } = require("../static/js/incident-logic.js");

test("BEH-2: includes only the filters that are set", () => {
  const params = buildIncidentQueryParams({ state: "new" }, 2, 25);
  assert.deepEqual(params, { state: "new", page: "2", page_size: "25" });
});

test("BEH-2: supports the full combination of state/category/account_id/escalated", () => {
  const params = buildIncidentQueryParams(
    { state: "in_progress", category: "billing", account_id: "ACCOUNT-1001", escalated: "true" },
    1, 50
  );
  assert.deepEqual(params, {
    state: "in_progress", category: "billing", account_id: "ACCOUNT-1001",
    escalated: "true", page: "1", page_size: "50",
  });
});

test("BEH-2: an empty-string filter value is omitted, not sent as a literal empty match", () => {
  const params = buildIncidentQueryParams({ state: "", category: "billing" }, 1, 50);
  assert.equal("state" in params, false);
  assert.equal(params.category, "billing");
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/beh-1-list-load.test.js tests_js/beh-2-list-filters.test.js`
Expected: FAIL — `buildIncidentQueryParams is not a function`, `shapePaginationInfo is not a
function`

- [ ] **Implement**

Add to `incident-logic.js`'s factory (extends Task 1's return object):

```javascript
  function buildIncidentQueryParams(filters, page, pageSize) {
    const params = {};
    if (filters && filters.state) params.state = filters.state;
    if (filters && filters.category) params.category = filters.category;
    if (filters && filters.account_id) params.account_id = filters.account_id;
    if (filters && filters.escalated) params.escalated = filters.escalated;
    if (page) params.page = String(page);
    if (pageSize) params.page_size = String(pageSize);
    return params;
  }

  function shapePaginationInfo(page, pageSize, total) {
    const totalPages = pageSize > 0 ? Math.max(1, Math.ceil(total / pageSize)) : 1;
    return { page, pageSize, total, totalPages, hasPrev: page > 1, hasNext: page < totalPages };
  }

  // ...
  return {
    INCIDENT_STATES, PRIORITIES, NOTE_TYPES, formatFetchError,
    buildIncidentQueryParams, shapePaginationInfo,
  };
```

Add to `incident.js` (extends Task 1's module):

```javascript
  const PAGE_SIZE = 50;
  let currentFilters = {};
  let currentPage = 1;

  function renderIncidentRow(incident) {
    const tr = document.createElement("tr");
    tr.dataset.number = incident.number;
    const cells = [
      incident.number, incident.short_description, incident.state,
      String(incident.priority), incident.category, incident.account_id,
      incident.escalated ? "Yes" : "No",
    ];
    for (const value of cells) {
      const td = document.createElement("td");
      td.textContent = value; // safe DOM insertion — never innerHTML (Postconditions)
      tr.appendChild(td);
    }
    return tr;
  }

  function renderIncidentList(page) {
    const body = document.getElementById("incidents-table-body");
    body.innerHTML = ""; // full replace — BEH-2/Postconditions: never mixes old+new results
    for (const incident of page.items) body.appendChild(renderIncidentRow(incident));
    const info = IncidentLogic.shapePaginationInfo(page.page, page.page_size, page.total);
    document.getElementById("incidents-page-info").textContent =
      `Page ${info.page} of ${info.totalPages} (${info.total} total)`;
    document.getElementById("incidents-prev-page").disabled = !info.hasPrev;
    document.getElementById("incidents-next-page").disabled = !info.hasNext;
  }

  async function loadIncidentList() {
    const params = IncidentLogic.buildIncidentQueryParams(currentFilters, currentPage, PAGE_SIZE);
    const query = new URLSearchParams(params).toString();
    try {
      const page = await fetchJson(`/incidents${query ? "?" + query : ""}`);
      clearError();
      renderIncidentList(page);
    } catch (err) {
      showError(IncidentLogic.formatFetchError("Loading incidents", err));
    }
  }

  function onFilterSubmit(event) {
    event.preventDefault();
    const form = event.target;
    currentFilters = {
      state: form.state.value, category: form.category.value,
      account_id: form.account_id.value, escalated: form.escalated.value,
    };
    currentPage = 1;
    loadIncidentList(); // fully replaces the table body — never merges with the prior filter set
  }

  function onPrevPage() {
    if (currentPage > 1) { currentPage -= 1; loadIncidentList(); }
  }

  function onNextPage() {
    currentPage += 1;
    loadIncidentList();
  }

  document.getElementById("incident-filter-form").addEventListener("submit", onFilterSubmit);
  document.getElementById("incidents-prev-page").addEventListener("click", onPrevPage);
  document.getElementById("incidents-next-page").addEventListener("click", onNextPage);
  document.addEventListener("DOMContentLoaded", loadIncidentList);

  window.IncidentApp = Object.assign(window.IncidentApp || {}, {
    fetchJson, showError, clearError, loadIncidentList, renderIncidentList, renderIncidentRow,
  });
```

Populate the `#filter-state` `<select>`'s options from `IncidentLogic.INCIDENT_STATES` in a small
`DOMContentLoaded`-time helper (added here, reused by Task 6/7 for `#create-state`/`#edit-state`):

```javascript
  function populateStateOptions(selectEl, includeBlank) {
    if (includeBlank) selectEl.appendChild(new Option("All", ""));
    for (const state of IncidentLogic.INCIDENT_STATES) selectEl.appendChild(new Option(state, state));
  }
  populateStateOptions(document.getElementById("filter-state"), true);
```

- [ ] **Verify test passes**

Run: `node --test tests_js/beh-1-list-load.test.js tests_js/beh-2-list-filters.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/incident-logic.js static/js/incident.js \
  tests_js/beh-1-list-load.test.js tests_js/beh-2-list-filters.test.js
git commit -m "feat(agent-ui): render filterable, paginated incident list"
```

---

### Task 3: Incident record view (fields + work-note timeline render) [specialist: none]

**Charter capability:** Incident record view; Work-note timeline + add form (render half)
**Depends on:** Task 2
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `tests_js/beh-3-record-view.test.js`, `tests_js/beh-4-work-note-timeline.test.js`
- Modify: `static/js/incident-logic.js` (add `shapeIncidentRecordFields`,
  `sortWorkNotesChronological`, `formatNullableField`)
- Modify: `static/js/incident.js` (add record load/render, list-row click-to-open,
  back-to-list); extends `tests_js/beh-9-error-formatting.test.js` with a 404 case

**Tests:** `tests_js/beh-3-record-view.test.js` (new — BEH-3); `beh-4-work-note-timeline.test.js`
(new — BEH-4); `beh-9-error-formatting.test.js` (extend — 404 row)

**Context to load:**
- Spec BEH-3, BEH-4, Postconditions
- `app/routers/incidents.py` `get_incident` (404 body); `app/routers/work_notes.py`
  `list_work_notes`

- [ ] **Write failing test**

```javascript
// tests_js/beh-3-record-view.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { shapeIncidentRecordFields, formatNullableField } = require("../static/js/incident-logic.js");

const INCIDENT = {
  number: "TICKET-004417", account_id: "ACCOUNT-1001", category: "billing",
  short_description: "Invoice mismatch", description: "Customer reports a mismatch.",
  state: "new", priority: 2, opened_at: "2026-09-01T00:00:00Z", resolved_at: null,
  assigned_to: null, assignment_group: "Support Tier 1", escalated: false,
};

test("BEH-3: every field is present, including null fields as explicit placeholders", () => {
  const fields = shapeIncidentRecordFields(INCIDENT);
  const byLabel = Object.fromEntries(fields.map((f) => [f.label, f.value]));
  assert.equal(byLabel["Number"], "TICKET-004417");
  assert.equal(byLabel["Assigned to"], "Unassigned");
  assert.equal(byLabel["Resolved at"], "Not resolved");
  assert.equal(byLabel["Assignment group"], "Support Tier 1");
});

test("formatNullableField: null/undefined/empty all resolve to the placeholder", () => {
  assert.equal(formatNullableField(null, "Unassigned"), "Unassigned");
  assert.equal(formatNullableField(undefined, "Unassigned"), "Unassigned");
  assert.equal(formatNullableField("dana", "Unassigned"), "dana");
});
```

```javascript
// tests_js/beh-4-work-note-timeline.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { sortWorkNotesChronological } = require("../static/js/incident-logic.js");

test("BEH-4: sorts notes ascending by created_at regardless of input order", () => {
  const notes = [
    { sys_id: "INTERACTION-0000002", created_at: "2026-09-02T00:00:00Z" },
    { sys_id: "INTERACTION-0000001", created_at: "2026-09-01T00:00:00Z" },
  ];
  const sorted = sortWorkNotesChronological(notes);
  assert.deepEqual(sorted.map((n) => n.sys_id), ["INTERACTION-0000001", "INTERACTION-0000002"]);
});

test("BEH-4: does not mutate the input array", () => {
  const notes = [{ created_at: "b" }, { created_at: "a" }];
  const copy = [...notes];
  sortWorkNotesChronological(notes);
  assert.deepEqual(notes, copy);
});

test("BEH-4: handles zero notes without error", () => {
  assert.deepEqual(sortWorkNotesChronological([]), []);
});
```

```javascript
// tests_js/beh-9-error-formatting.test.js (append)
test("BEH-9/UI_NOT_FOUND: a 404 on GET /incidents/{number} surfaces a not-found message", () => {
  const { formatFetchError } = require("../static/js/incident-logic.js");
  const msg = formatFetchError("Loading incident TICKET-999999", {
    status: 404, message: "Incident TICKET-999999 not found",
  });
  assert.match(msg, /TICKET-999999/);
  assert.match(msg, /not found/);
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/beh-3-record-view.test.js tests_js/beh-4-work-note-timeline.test.js`
Expected: FAIL — `shapeIncidentRecordFields is not a function`, `sortWorkNotesChronological is
not a function`

- [ ] **Implement**

Add to `incident-logic.js`:

```javascript
  function formatNullableField(value, placeholder) {
    return value === null || value === undefined || value === "" ? placeholder : value;
  }

  function shapeIncidentRecordFields(incident) {
    return [
      { label: "Number", value: incident.number },
      { label: "Account", value: incident.account_id },
      { label: "Category", value: incident.category },
      { label: "Short description", value: incident.short_description },
      { label: "Description", value: incident.description },
      { label: "State", value: incident.state },
      { label: "Priority", value: String(incident.priority) },
      { label: "Opened at", value: incident.opened_at },
      { label: "Resolved at", value: formatNullableField(incident.resolved_at, "Not resolved") },
      { label: "Assigned to", value: formatNullableField(incident.assigned_to, "Unassigned") },
      { label: "Assignment group",
        value: formatNullableField(incident.assignment_group, "Unassigned") },
      { label: "Escalated", value: incident.escalated ? "Yes" : "No" },
    ];
  }

  function sortWorkNotesChronological(notes) {
    return [...(Array.isArray(notes) ? notes : [])].sort((a, b) =>
      a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : 0
    );
  }

  // ...
  return {
    INCIDENT_STATES, PRIORITIES, NOTE_TYPES, formatFetchError,
    buildIncidentQueryParams, shapePaginationInfo,
    formatNullableField, shapeIncidentRecordFields, sortWorkNotesChronological,
  };
```

Add to `incident.js`:

```javascript
  let currentIncident = null;

  function renderRecordFields(incident) {
    const dl = document.getElementById("record-fields");
    dl.innerHTML = ""; // full replace — Postconditions: no stale field survives a new load
    for (const { label, value } of IncidentLogic.shapeIncidentRecordFields(incident)) {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value; // safe DOM insertion for user-supplied text fields too
      dl.appendChild(dt);
      dl.appendChild(dd);
    }
    document.getElementById("record-number").textContent = incident.number;
  }

  function renderWorkNoteRow(note) {
    const li = document.createElement("li");
    const meta = document.createElement("p");
    meta.className = "work-note-meta";
    meta.textContent = `${note.created_by} · ${note.note_type} · ${note.created_at}`;
    const body = document.createElement("p");
    body.textContent = note.body; // safe DOM insertion — created_by/body are unguarded free text
    li.appendChild(meta);
    li.appendChild(body);
    return li;
  }

  function renderWorkNoteTimeline(notes) {
    const ol = document.getElementById("work-notes-timeline");
    ol.innerHTML = "";
    for (const note of IncidentLogic.sortWorkNotesChronological(notes)) {
      ol.appendChild(renderWorkNoteRow(note));
    }
  }

  async function loadIncidentRecord(number) {
    try {
      const incident = await fetchJson(`/incidents/${number}`);
      currentIncident = incident;
      clearError();
      renderRecordFields(incident);
      document.getElementById("incident-list-view").hidden = true;
      document.getElementById("create-incident").hidden = true;
      document.getElementById("incident-record-view").hidden = false;
    } catch (err) {
      showError(IncidentLogic.formatFetchError(`Loading incident ${number}`, err));
      return;
    }
    try {
      const notePage = await fetchJson(`/incidents/${number}/work_notes`);
      renderWorkNoteTimeline(notePage.items);
    } catch (err) {
      showError(IncidentLogic.formatFetchError("Loading work notes", err));
    }
  }

  function onIncidentRowClick(event) {
    const row = event.target.closest("tr[data-number]");
    if (row) loadIncidentRecord(row.dataset.number);
  }

  function onBackToList() {
    document.getElementById("incident-record-view").hidden = true;
    document.getElementById("incident-list-view").hidden = false;
    currentIncident = null;
  }

  document.getElementById("incidents-table-body").addEventListener("click", onIncidentRowClick);
  document.getElementById("back-to-list").addEventListener("click", onBackToList);

  window.IncidentApp = Object.assign(window.IncidentApp || {}, {
    loadIncidentRecord, renderRecordFields, renderWorkNoteTimeline,
  });
```

- [ ] **Verify test passes**

Run: `node --test tests_js/beh-3-record-view.test.js tests_js/beh-4-work-note-timeline.test.js tests_js/beh-9-error-formatting.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/incident-logic.js static/js/incident.js \
  tests_js/beh-3-record-view.test.js tests_js/beh-4-work-note-timeline.test.js \
  tests_js/beh-9-error-formatting.test.js
git commit -m "feat(agent-ui): render incident record view and work-note timeline"
```

---

### Task 4: Add work note [specialist: none]

**Charter capability:** Work-note timeline + add form (write half)
**Depends on:** Task 3
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `tests_js/beh-5-add-work-note.test.js`
- Modify: `static/js/incident-logic.js` (add `validateWorkNoteForm`)
- Modify: `static/js/incident.js` (add-work-note submit handler, optimistic-append wiring)

**Tests:** `tests_js/beh-5-add-work-note.test.js` (new — BEH-5)

**Context to load:**
- Spec BEH-5, Preconditions (`created_by` free-text)
- `app/routers/work_notes.py` `create_work_note` (required fields, 201 shape, 404 row)

- [ ] **Write failing test**

```javascript
// tests_js/beh-5-add-work-note.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { validateWorkNoteForm, NOTE_TYPES } = require("../static/js/incident-logic.js");

test("BEH-5: all three fields required, none constrained beyond note_type's enum", () => {
  const result = validateWorkNoteForm({ created_by: "", note_type: "comment", body: "hi" });
  assert.equal(result.valid, false);
  assert.ok(result.errors.created_by);
});

test("BEH-5: created_by accepts any free-text value, including 'assist' or 'customer'", () => {
  for (const author of ["assist", "customer", "any-agent-name"]) {
    const result = validateWorkNoteForm({ created_by: author, note_type: "comment", body: "hi" });
    assert.equal(result.valid, true, `expected ${author} to be accepted`);
  }
});

test("BEH-5: note_type must be one of the four fixed values", () => {
  const result = validateWorkNoteForm({ created_by: "assist", note_type: "not-real", body: "hi" });
  assert.equal(result.valid, false);
  assert.ok(result.errors.note_type);
});

test("NOTE_TYPES matches the four values the API validates against", () => {
  assert.deepEqual(NOTE_TYPES, ["comment", "work_note", "state_change", "proposal_sent"]);
});

test("BEH-5: a fully valid form has no errors", () => {
  const result = validateWorkNoteForm({ created_by: "assist", note_type: "work_note", body: "Called customer." });
  assert.deepEqual(result.errors, {});
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/beh-5-add-work-note.test.js`
Expected: FAIL — `validateWorkNoteForm is not a function`

- [ ] **Implement**

Add to `incident-logic.js`:

```javascript
  function validateWorkNoteForm(fields) {
    const errors = {};
    if (!fields.created_by || !fields.created_by.trim()) {
      errors.created_by = "Created by is required";
    }
    if (!fields.note_type || !NOTE_TYPES.includes(fields.note_type)) {
      errors.note_type = `Note type must be one of: ${NOTE_TYPES.join(", ")}`;
    }
    if (!fields.body || !fields.body.trim()) {
      errors.body = "Body is required";
    }
    return { valid: Object.keys(errors).length === 0, errors };
  }

  // ...
  return {
    INCIDENT_STATES, PRIORITIES, NOTE_TYPES, formatFetchError,
    buildIncidentQueryParams, shapePaginationInfo,
    formatNullableField, shapeIncidentRecordFields, sortWorkNotesChronological,
    validateWorkNoteForm,
  };
```

Add to `incident.js` (populates `#note-note_type` from `NOTE_TYPES`, validates, posts, appends
without a full reload — BEH-5's "no page reload" requirement):

```javascript
  function populateNoteTypeOptions() {
    const select = document.getElementById("note-note_type");
    for (const type of IncidentLogic.NOTE_TYPES) select.appendChild(new Option(type, type));
  }
  populateNoteTypeOptions();

  function showFormError(elementId, message) {
    const el = document.getElementById(elementId);
    el.textContent = message;
    el.hidden = false;
  }

  function clearFormError(elementId) {
    document.getElementById(elementId).hidden = true;
  }

  async function onAddWorkNoteSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const fields = {
      created_by: form.created_by.value, note_type: form.note_type.value, body: form.body.value,
    };
    const { valid, errors } = IncidentLogic.validateWorkNoteForm(fields);
    if (!valid) {
      showFormError("add-work-note-error", Object.values(errors)[0]);
      return; // client-side block: fields the API also requires, no request sent
    }
    clearFormError("add-work-note-error");
    try {
      const created = await fetchJson(`/incidents/${currentIncident.number}/work_notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fields),
      });
      document.getElementById("work-notes-timeline").appendChild(renderWorkNoteRow(created));
      form.reset();
    } catch (err) {
      showFormError("add-work-note-error", IncidentLogic.formatFetchError("Adding work note", err));
    }
  }

  document.getElementById("add-work-note-form").addEventListener("submit", onAddWorkNoteSubmit);
```

`renderWorkNoteRow(created)` appends the server's own response object directly to the timeline
`<ol>` — no full-list refetch — satisfying BEH-5's "appends the new note to the visible timeline
without a full page reload" exactly, while still rendering through the same safe-DOM row builder
Task 3 defined.

- [ ] **Verify test passes**

Run: `node --test tests_js/beh-5-add-work-note.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/incident-logic.js static/js/incident.js tests_js/beh-5-add-work-note.test.js
git commit -m "feat(agent-ui): add work-note form with optimistic timeline append"
```

---

### Task 5: SLA panel [specialist: none]

**Charter capability:** SLA panel
**Depends on:** Task 3
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `tests_js/beh-6-sla-panel.test.js`
- Modify: `static/js/incident-logic.js` (add `shapeSlaRows`)
- Modify: `static/js/incident.js` (SLA fetch/render wiring, added to `loadIncidentRecord`)
- Modify: `static/css/console.css` (fill in the `.sla-breached` placeholder from Task 1)

**Tests:** `tests_js/beh-6-sla-panel.test.js` (new — BEH-6)

**Context to load:**
- Spec BEH-6, System Constitution Reference Principle 6
- `app/routers/sla.py` `list_sla_records` (`incident_number` filter, `TaskSlaRead` shape)

- [ ] **Write failing test**

```javascript
// tests_js/beh-6-sla-panel.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { shapeSlaRows } = require("../static/js/incident-logic.js");

test("BEH-6: every field is passed through unchanged, plus a breach-flag class", () => {
  const rows = shapeSlaRows([
    { sys_id: "SLA-0001", incident_number: "TICKET-004417", sla_definition: "first_response",
      target_minutes: 30, actual_minutes: 45, has_breached: true, business_time_only: false },
  ]);
  assert.equal(rows[0].sla_definition, "first_response");
  assert.equal(rows[0].actual_minutes, 45);
  assert.equal(rows[0].breachClass, "sla-breached");
});

test("BEH-6: a non-breached row gets no breach-flag class, factually — not hidden either way", () => {
  const rows = shapeSlaRows([
    { sys_id: "SLA-0002", has_breached: false, target_minutes: 240, actual_minutes: 120,
      sla_definition: "resolution", business_time_only: true, incident_number: "TICKET-004417" },
  ]);
  assert.equal(rows[0].breachClass, "");
});

test("BEH-6: never omits or filters any row — this is data shaping, not a block/allow decision", () => {
  const rows = shapeSlaRows([{ has_breached: true }, { has_breached: false }]);
  assert.equal(rows.length, 2);
});

test("BEH-6: an empty/missing input yields an empty array, not a crash", () => {
  assert.deepEqual(shapeSlaRows(undefined), []);
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/beh-6-sla-panel.test.js`
Expected: FAIL — `shapeSlaRows is not a function`

- [ ] **Implement**

Add to `incident-logic.js`:

```javascript
  function shapeSlaRows(rows) {
    // A breach is a fact this function surfaces, never a condition it filters, hides, or
    // annotates as an error — constitution Principle 6 / spec BEH-6.
    return (Array.isArray(rows) ? rows : []).map((r) => ({
      ...r,
      breachClass: r.has_breached ? "sla-breached" : "",
    }));
  }

  // ...
  return {
    INCIDENT_STATES, PRIORITIES, NOTE_TYPES, formatFetchError,
    buildIncidentQueryParams, shapePaginationInfo,
    formatNullableField, shapeIncidentRecordFields, sortWorkNotesChronological,
    validateWorkNoteForm, shapeSlaRows,
  };
```

Add to `incident.js` (extends `loadIncidentRecord` from Task 3 with a third parallel fetch):

```javascript
  function renderSlaRow(row) {
    const tr = document.createElement("tr");
    if (row.breachClass) tr.className = row.breachClass;
    const cells = [
      row.sla_definition, String(row.target_minutes),
      row.actual_minutes === null ? "—" : String(row.actual_minutes),
      row.has_breached ? "Yes" : "No", row.business_time_only ? "Yes" : "No",
    ];
    for (const value of cells) {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    }
    return tr;
  }

  function renderSlaPanel(rows) {
    const body = document.getElementById("sla-table-body");
    body.innerHTML = "";
    for (const row of IncidentLogic.shapeSlaRows(rows)) body.appendChild(renderSlaRow(row));
  }

  // Extend loadIncidentRecord (Task 3) with the SLA fetch, run alongside the work-notes fetch:
  async function loadIncidentRecord(number) {
    try {
      const incident = await fetchJson(`/incidents/${number}`);
      currentIncident = incident;
      clearError();
      renderRecordFields(incident);
      document.getElementById("incident-list-view").hidden = true;
      document.getElementById("create-incident").hidden = true;
      document.getElementById("incident-record-view").hidden = false;
    } catch (err) {
      showError(IncidentLogic.formatFetchError(`Loading incident ${number}`, err));
      return;
    }
    try {
      const notePage = await fetchJson(`/incidents/${number}/work_notes`);
      renderWorkNoteTimeline(notePage.items);
    } catch (err) {
      showError(IncidentLogic.formatFetchError("Loading work notes", err));
    }
    try {
      const slaPage = await fetchJson(`/sla?incident_number=${encodeURIComponent(number)}`);
      renderSlaPanel(slaPage.items);
    } catch (err) {
      showError(IncidentLogic.formatFetchError("Loading SLA records", err));
    }
  }
```

Add to `console.css` (fills the Task 1 placeholder):

```css
.sla-breached {
  /* Visibly distinct, never alarming or apologetic — a breach is a fact (Principle 6). */
  background: #fff3e0;
  font-weight: 600;
}
```

- [ ] **Verify test passes**

Run: `node --test tests_js/beh-6-sla-panel.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/incident-logic.js static/js/incident.js static/css/console.css \
  tests_js/beh-6-sla-panel.test.js
git commit -m "feat(agent-ui): render SLA panel with factual breach highlighting"
```

---

### Task 6: Edit incident fields [Confirm no guard exists] [specialist: none]

> **Note on task purpose:** BEH-7 and the charter's unguarded-editing note require saving a
> `state`/`priority`/`assigned_to`/`assignment_group` change to succeed unconditionally — including
> a transition that resolves/closes an Incident with an open `first_response` SLA breach — with no
> confirmation dialog, no warning banner, and no client-side check blocking the save. The test
> below is written so that adding *any* guard to `diffIncidentFields` or the submit handler (a
> state-transition check, an SLA lookup, a confirmation prompt) would make it fail — the absence
> of such logic in the Implement step is the behavior being tested, mirroring
> `mcp-server/incident-tools.plan.md` Task 5's identical proof at the MCP layer.

**Charter capability:** Edit incident fields
**Depends on:** Task 3
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `tests_js/beh-7-edit-incident.test.js`
- Modify: `static/js/incident-logic.js` (add `diffIncidentFields`)
- Modify: `static/js/incident.js` (edit-form population + submit handler); extends
  `tests_js/beh-9-error-formatting.test.js` with a 422 case

**Tests:** `tests_js/beh-7-edit-incident.test.js` (new — BEH-7, including the no-guard
regression); `beh-9-error-formatting.test.js` (extend — 422 row)

**Context to load:**
- Spec BEH-7, Postconditions, System Constitution Reference Principle 5
- `app/routers/incidents.py` `patch_incident` (`_PATCHABLE_FIELDS`, no guard, 404 row)

- [ ] **Write failing test**

```javascript
// tests_js/beh-7-edit-incident.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { diffIncidentFields } = require("../static/js/incident-logic.js");

const ORIGINAL = {
  number: "TICKET-004417", state: "in_progress", priority: 2,
  assigned_to: null, assignment_group: "Support Tier 1",
};

test("BEH-7: diffs only the fields that actually changed", () => {
  const patch = diffIncidentFields(ORIGINAL, { ...ORIGINAL, state: "resolved" });
  assert.deepEqual(patch, { state: "resolved" });
});

test("BEH-7: an edited form with no actual change produces an empty patch", () => {
  const patch = diffIncidentFields(ORIGINAL, { ...ORIGINAL });
  assert.deepEqual(patch, {});
});

test("BEH-7: priority is compared numerically, not as a select's string value", () => {
  const patch = diffIncidentFields(ORIGINAL, { ...ORIGINAL, priority: "4" });
  assert.deepEqual(patch, { priority: 4 });
});

test("BEH-7: an emptied assigned_to/assignment_group diffs to null, not an empty string", () => {
  const patch = diffIncidentFields(ORIGINAL, { ...ORIGINAL, assignment_group: "" });
  assert.deepEqual(patch, { assignment_group: null });
});

test("BEH-7 [no-guard regression]: resolving with an open first_response breach diffs and "
  + "submits identically to any other state change — no field is added, removed, or annotated",
  () => {
    // This UI has no SLA data at diff time (SLA rows are a separate fetch — see Task 5) and
    // diffIncidentFields never inspects them even by accident: same shape whether or not a
    // breach exists, because the function only ever compares the four patchable fields.
    const patch = diffIncidentFields(
      { ...ORIGINAL, state: "in_progress" },
      { ...ORIGINAL, state: "resolved" }
    );
    assert.deepEqual(Object.keys(patch), ["state"]);
    assert.equal(patch.state, "resolved");
  }
);

test("BEH-7: number/account_id/opened_at are never patchable fields, even if present on the object", () => {
  const patch = diffIncidentFields(ORIGINAL, { ...ORIGINAL, number: "TICKET-999999", state: "closed" });
  assert.equal("number" in patch, false);
  assert.deepEqual(patch, { state: "closed" });
});
```

```javascript
// tests_js/beh-9-error-formatting.test.js (append)
test("BEH-9/UI_VALIDATION_ERROR: a 422 on PATCH names the invalid field verbatim", () => {
  const { formatFetchError } = require("../static/js/incident-logic.js");
  const msg = formatFetchError("Saving incident", {
    status: 422, message: "priority must be one of: 1, 2, 3, 4",
  });
  assert.match(msg, /priority must be one of/);
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/beh-7-edit-incident.test.js`
Expected: FAIL — `diffIncidentFields is not a function`

- [ ] **Implement**

Add to `incident-logic.js`:

```javascript
  const PATCHABLE_INCIDENT_FIELDS = ["state", "priority", "assigned_to", "assignment_group"];

  function diffIncidentFields(original, edited) {
    // Pure change-detector only — no branch here inspects what the new state *means* (e.g.
    // resolving with an open SLA breach). Adding such a branch would violate BEH-7 / the
    // constitution's Principle 5, and is exactly the regression the test suite above guards
    // against.
    const patch = {};
    for (const key of PATCHABLE_INCIDENT_FIELDS) {
      let newValue = edited[key];
      if (newValue === undefined) continue;
      if (key === "priority" && newValue !== "") newValue = Number(newValue);
      if ((key === "assigned_to" || key === "assignment_group") && newValue === "") {
        newValue = null;
      }
      if (newValue !== original[key]) patch[key] = newValue;
    }
    return patch;
  }

  // ...
  return {
    INCIDENT_STATES, PRIORITIES, NOTE_TYPES, formatFetchError,
    buildIncidentQueryParams, shapePaginationInfo,
    formatNullableField, shapeIncidentRecordFields, sortWorkNotesChronological,
    validateWorkNoteForm, shapeSlaRows, diffIncidentFields,
  };
```

Add to `incident.js` (populate the edit form from `currentIncident` when the record loads,
extending `renderRecordFields`; wire the submit handler):

```javascript
  function populateSelectOptions(selectEl, values) {
    selectEl.innerHTML = "";
    for (const value of values) selectEl.appendChild(new Option(String(value), String(value)));
  }
  populateSelectOptions(document.getElementById("edit-state"), IncidentLogic.INCIDENT_STATES);
  populateSelectOptions(document.getElementById("edit-priority"), IncidentLogic.PRIORITIES);

  function populateEditForm(incident) {
    document.getElementById("edit-state").value = incident.state;
    document.getElementById("edit-priority").value = String(incident.priority);
    document.getElementById("edit-assigned_to").value = incident.assigned_to || "";
    document.getElementById("edit-assignment_group").value = incident.assignment_group || "";
  }

  // Extend renderRecordFields (Task 3) to also populate the edit form:
  function renderRecordFields(incident) {
    const dl = document.getElementById("record-fields");
    dl.innerHTML = "";
    for (const { label, value } of IncidentLogic.shapeIncidentRecordFields(incident)) {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      dl.appendChild(dt);
      dl.appendChild(dd);
    }
    document.getElementById("record-number").textContent = incident.number;
    populateEditForm(incident);
  }

  async function onEditIncidentSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const edited = {
      state: form.state.value, priority: form.priority.value,
      assigned_to: form.assigned_to.value, assignment_group: form.assignment_group.value,
    };
    const patch = IncidentLogic.diffIncidentFields(currentIncident, edited);
    if (Object.keys(patch).length === 0) {
      clearFormError("edit-incident-error");
      return; // nothing changed — no network call, no third "nothing happened" state
    }
    // No confirmation dialog, no state-transition check — BEH-7 / constitution Principle 5.
    // The save either succeeds (200) or fails with the API's own 422; there is no other outcome.
    try {
      const updated = await fetchJson(`/incidents/${currentIncident.number}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      currentIncident = updated;
      clearFormError("edit-incident-error");
      renderRecordFields(updated); // reflects the server's own post-save state (Postconditions)
    } catch (err) {
      showFormError("edit-incident-error", IncidentLogic.formatFetchError("Saving incident", err));
    }
  }

  document.getElementById("edit-incident-form").addEventListener("submit", onEditIncidentSubmit);
```

- [ ] **Verify test passes**

Run: `node --test tests_js/beh-7-edit-incident.test.js tests_js/beh-9-error-formatting.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/incident-logic.js static/js/incident.js \
  tests_js/beh-7-edit-incident.test.js tests_js/beh-9-error-formatting.test.js
git commit -m "feat(agent-ui): add unguarded incident field editing"
```

---

### Task 7: Create incident [specialist: none]

**Charter capability:** Create incident
**Depends on:** Task 2, Task 6 (reuses the `populateSelectOptions` helper Task 6 adds to
`incident.js` for `#edit-state`/`#edit-priority`, applying it here to `#create-state`/
`#create-priority`)
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `tests_js/beh-8-create-incident.test.js`
- Modify: `static/js/incident-logic.js` (add `validateCreateIncidentForm`)
- Modify: `static/js/incident.js` (create-form population + submit handler, navigate-on-success);
  extends `tests_js/beh-9-error-formatting.test.js` with a create-specific 422 case

**Tests:** `tests_js/beh-8-create-incident.test.js` (new — BEH-8)

**Context to load:**
- Spec BEH-8
- `app/routers/incidents.py` `create_incident` (six required fields, defaults, 422 row)

- [ ] **Write failing test**

```javascript
// tests_js/beh-8-create-incident.test.js
const test = require("node:test");
const assert = require("node:assert/strict");
const { validateCreateIncidentForm } = require("../static/js/incident-logic.js");

const VALID = {
  account_id: "ACCOUNT-1001", category: "billing", short_description: "Invoice mismatch",
  description: "Customer reports a mismatch.", state: "new", priority: "2",
};

test("BEH-8: all six required fields present passes validation", () => {
  assert.equal(validateCreateIncidentForm(VALID).valid, true);
});

for (const missing of Object.keys(VALID)) {
  test(`BEH-8: missing ${missing} fails validation and names the field`, () => {
    const fields = { ...VALID, [missing]: "" };
    const result = validateCreateIncidentForm(fields);
    assert.equal(result.valid, false);
    assert.ok(result.errors[missing]);
  });
}

test("BEH-8: category has no fixed enum at this layer — any non-empty value passes", () => {
  const result = validateCreateIncidentForm({ ...VALID, category: "anything-goes" });
  assert.equal(result.valid, true);
});
```

```javascript
// tests_js/beh-9-error-formatting.test.js (append)
test("BEH-9/UI_VALIDATION_ERROR: create-incident 422 names the invalid field", () => {
  const { formatFetchError } = require("../static/js/incident-logic.js");
  const msg = formatFetchError("Creating incident", {
    status: 422, message: "priority is required",
  });
  assert.match(msg, /priority is required/);
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/beh-8-create-incident.test.js`
Expected: FAIL — `validateCreateIncidentForm is not a function`

- [ ] **Implement**

Add to `incident-logic.js`:

```javascript
  const REQUIRED_CREATE_FIELDS = [
    "account_id", "category", "short_description", "description", "state", "priority",
  ];

  function validateCreateIncidentForm(fields) {
    const errors = {};
    for (const key of REQUIRED_CREATE_FIELDS) {
      const value = fields[key];
      if (value === undefined || value === null || String(value).trim() === "") {
        errors[key] = `${key} is required`;
      }
    }
    return { valid: Object.keys(errors).length === 0, errors };
    // category is deliberately unconstrained here — app/models.py's IncidentCreate.category
    // is a plain str with no Literal enum, so this UI invents no enum the API doesn't have.
  }

  // ...
  return {
    INCIDENT_STATES, PRIORITIES, NOTE_TYPES, formatFetchError,
    buildIncidentQueryParams, shapePaginationInfo,
    formatNullableField, shapeIncidentRecordFields, sortWorkNotesChronological,
    validateWorkNoteForm, shapeSlaRows, diffIncidentFields, validateCreateIncidentForm,
  };
```

Add to `incident.js`:

```javascript
  populateSelectOptions(document.getElementById("create-state"), IncidentLogic.INCIDENT_STATES);
  populateSelectOptions(document.getElementById("create-priority"), IncidentLogic.PRIORITIES);

  document.getElementById("open-create-incident").addEventListener("click", () => {
    document.getElementById("incident-list-view").hidden = true;
    document.getElementById("create-incident").hidden = false;
  });
  document.getElementById("cancel-create-incident").addEventListener("click", (event) => {
    event.preventDefault();
    document.getElementById("create-incident-form").reset();
    clearFormError("create-incident-error");
    document.getElementById("create-incident").hidden = true;
    document.getElementById("incident-list-view").hidden = false;
  });

  async function onCreateIncidentSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const fields = {
      account_id: form.account_id.value, category: form.category.value,
      short_description: form.short_description.value, description: form.description.value,
      state: form.state.value, priority: form.priority.value,
    };
    const { valid, errors } = IncidentLogic.validateCreateIncidentForm(fields);
    if (!valid) {
      showFormError("create-incident-error", Object.values(errors)[0]);
      return;
    }
    clearFormError("create-incident-error");
    try {
      const created = await fetchJson("/incidents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...fields, priority: Number(fields.priority) }),
      });
      form.reset();
      document.getElementById("create-incident").hidden = true;
      await loadIncidentRecord(created.number); // BEH-8: navigate to the new record on success
    } catch (err) {
      showFormError("create-incident-error", IncidentLogic.formatFetchError("Creating incident", err));
    }
  }

  document.getElementById("create-incident-form").addEventListener("submit", onCreateIncidentSubmit);
```

- [ ] **Verify test passes**

Run: `node --test tests_js/beh-8-create-incident.test.js tests_js/beh-9-error-formatting.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/incident-logic.js static/js/incident.js \
  tests_js/beh-8-create-incident.test.js tests_js/beh-9-error-formatting.test.js
git commit -m "feat(agent-ui): add create-incident form with navigate-on-success"
```

---

## Quality Gates

`.context-index/governance/gates.yaml` exists, so its gate definitions govern instead of the
constitution's Commands section. After Task 1 this plan's changes add one gate to that file; the
full resolved set after all 7 tasks:

- **Tests pass:** `python3 -m pytest -q` (gate `test`) — covers `tests/test_static_assets.py`
  plus every existing `itsm-api`/mcp-server test (unaffected by this spec).
- **JS unit tests pass:** `node --test tests_js/` (gate `test-js`, added by Task 1) — covers all
  nine `tests_js/beh-*.test.js` suites (BEH-1 through BEH-9).
- **Lint passes:** `ruff check .` (gate `lint`) — Python only; `static/`, `tests_js/`, and the new
  `*.js`/`*.html`/`*.css` files fall outside ruff's scope, so no lint config change is needed.
- `integration-test` gate stays unwired (`command: ""`) — unaffected by this spec.
- `e2e-smoke` gate (`python3 -m pytest -q tests_e2e/`) is unaffected — this plan's `GET /` change
  is confirmed compatible with `start_itsm_api()`'s status-only poll (see Design decision above);
  no task modifies `tests_e2e/`.
- All acceptance criteria from `incident-console.spec.md` satisfied: BEH-1 through BEH-9 each
  traced to exactly one task above (BEH-9's core formatter in Task 1, extended per-entity in
  Tasks 3/6/7), plus the spec's three Error Cases rows (`UI_FETCH_FAILED`, `UI_VALIDATION_ERROR`,
  `UI_NOT_FOUND` — all exercised via `formatFetchError`/`tests_js/beh-9-error-formatting.test.js`).
- Task Map scoping confirmed: no task in this plan adds `.nav-item` markup, a `data-view`
  attribute, or any cross-view switching logic — `tests/test_static_assets.py`'s
  `test_root_serves_incident_console_shell` asserts `"nav-item" not in body` as a standing
  regression guard for that boundary.

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are
recorded in the validation report (`.validate.md`), not in this plan.
