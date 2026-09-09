# Implementation Plan: Escalations screen — "New Escalation" create form

> **Methodology:** adev
> **Charter:** .context-index/specs/features/agent-ui/charter.md
> **Spec:** .context-index/specs/features/agent-ui/escalations-directory-nav-rev-3-create-escalation.spec.md
> **Review:** PASS_WITH_NOTES (2026-09-09)
> **Platform:** Static HTML/CSS/vanilla JS (UMD logic modules) served by itsm-api's FastAPI process; Python 3.11 backend; tests via `node --test` (tests_js) and `pytest` + Playwright (tests_e2e).

**Goal:** Add a "New Escalation" form to the Escalations screen that calls `POST /escalations`, closing out the agent-ui charter's last dependency on itsm-api's now-shipped create-escalation endpoint.

**Architecture:** Mirror the existing create-incident pattern exactly: a hidden `<section>` with an open/cancel toggle and a form, a pure-logic UMD module (`escalations-logic.js`) providing validation and payload-building functions unit-tested in isolation, and a thin DOM-wiring layer (`escalations.js`) that calls the pure functions, hits `POST /escalations`, and prepends the result to the in-memory `escalationsCache` without a full reload. Reuses `UiErrors.formatApiError` for fetch failures (BEH-9) and the existing `showEscalationsError` element for surfacing them.

**Review notes addressed:** CON-1 (missing e2e coverage) → Task 4 adds `tests_e2e/test_ui_create_escalation_e2e.py` with three scenarios (BEH-6/7 success, BEH-8 client-side validation, and BEH-9 a genuine `page.route(...).abort()` network failure — mirroring `tests_e2e/test_ui_error_path_e2e.py`'s precedent, not a mocked fetch), so the `catch` branch added in Task 3 is actually exercised. SUG-1 (safe-DOM rendering) → Task 3 explicitly reuses `renderEscalationsTable`'s existing `textContent`-only cell-rendering path for the prepended row rather than introducing a new render path.

---

## File Structure

**Modify:**
- `static/index.html` — add a "New Escalation" toggle button + form section inside `#view-escalations`, mirroring `#create-incident`'s markup shape (lines 141-152 today).
- `static/js/escalations-logic.js` — add `validateCreateEscalationForm(fields)` and `buildEscalationCreatePayload(fields)`, mirroring `incident-logic.js`'s `validateCreateIncidentForm`.
- `static/js/escalations.js` — wire the open/cancel/submit handlers for the new form; on success, prepend the created Escalation into `escalationsCache` and re-render via the existing `renderEscalationsTable`.

**Create:**
- `tests_js/escalations-beh-6-7-create-payload.test.js` — unit tests for `buildEscalationCreatePayload` (required-only and required+optional cases).
- `tests_js/escalations-beh-8-validation.test.js` — unit tests for `validateCreateEscalationForm` (missing `account_id`/`summary`).
- `tests_e2e/test_ui_create_escalation_e2e.py` — real-browser coverage: successful create (BEH-6/7) and a failed create retaining form values (BEH-9), mirroring `tests_e2e/test_ui_create_incident_e2e.py`.

**Reference (read, do not modify):**
- `static/js/incident.js:330-370` — the create-incident open/cancel/submit pattern this task mirrors.
- `static/js/incident-logic.js:120-135` — `validateCreateIncidentForm`, the pattern for `validateCreateEscalationForm`.
- `static/js/escalations.js` (current) — `renderEscalationsTable`, `loadEscalationsView`, `showEscalationsError` — reused, not replaced.
- `tests_e2e/test_ui_create_incident_e2e.py` — e2e pattern to mirror.
- `tests_js/escalations-beh-3-patch-payload.test.js` — existing unit-test style for this module.

## Context Packets

### Task 1 Context
- Spec: `.context-index/specs/features/agent-ui/escalations-directory-nav-rev-3-create-escalation.spec.md` (BEH-6, BEH-7, BEH-8)
- Base spec: `.context-index/specs/features/agent-ui/escalations-directory-nav.spec.md` (Escalations screen markup conventions)
- Source: `static/index.html` lines 75-92 (`#create-incident` section, the pattern to mirror) and 141-152 (`#view-escalations`, the section to extend)

### Task 2 Context
- Spec: `.context-index/specs/features/agent-ui/escalations-directory-nav-rev-3-create-escalation.spec.md` (BEH-6, BEH-7, BEH-8)
- Source: `static/js/escalations-logic.js` (full — this is the file being extended)
- Sample pattern: `static/js/incident-logic.js:120-135` (`validateCreateIncidentForm`)
- Existing test style: `tests_js/escalations-beh-3-patch-payload.test.js`

### Task 3 Context
- Spec: `.context-index/specs/features/agent-ui/escalations-directory-nav-rev-3-create-escalation.spec.md` (BEH-6, BEH-7, BEH-8, BEH-9)
- Base spec: `.context-index/specs/features/agent-ui/escalations-directory-nav.spec.md` (BEH-5, error-surfacing pattern; safe-DOM invariant)
- Source: `static/js/escalations.js` (full), `static/js/incident.js:342-368` (`onCreateIncidentSubmit`, the wiring pattern), `static/js/ui-errors.js` (`formatApiError`)

### Task 4 Context
- Spec: `.context-index/specs/features/agent-ui/escalations-directory-nav-rev-3-create-escalation.spec.md` (BEH-6, BEH-7, BEH-8, BEH-9, Acceptance Criteria)
- Sample: `tests_e2e/test_ui_create_incident_e2e.py` (structure to mirror)
- Fixtures: `tests_e2e/conftest.py` (`page`, `ui_app_server` fixtures — reused, not modified)

## Parallelization

- Group A (sequential): Task 1 → Task 2 → Task 3 → Task 4 (each depends on the previous: markup before logic before wiring before e2e)

No independent groups — this is a small, single-surface change with a strict build order (DOM targets must exist before wiring code references them; wiring must exist before e2e can drive it).

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | New Escalation form markup | small | unit | — | 0 create, 1 modify |
| 2 | Create-escalation validation & payload logic | medium | unit | Task 1 | 2 create, 1 modify |
| 3 | Create-escalation wiring | medium | unit | Task 1, Task 2 | 0 create, 1 modify |
| 4 | Create-escalation e2e coverage | medium | e2e | Task 3 | 1 create, 0 modify |

## Task Structure

### Task 1: New Escalation form markup [specialist: none]

**Charter capability:** Create escalation
**Strategy:** unit (source: fallback, confidence: high — this task is markup-only; verified by Task 2/3's tests exercising the resulting DOM ids)
**Files:**
- Modify: `static/index.html:141-152` (the `#view-escalations` section)

**Tests:** `tests_js/escalations-beh-6-7-create-payload.test.js` (Task 2 creates this; Task 1's markup ids are exercised indirectly through Task 3's wiring and Task 4's e2e test, since static markup has no unit-testable logic of its own)

**Context to load:**
- `static/index.html:75-92` (`#create-incident` — the pattern to mirror exactly: toggle button, hidden section, form, cancel button, inline error `<p>`)

- [ ] **Write failing test**

No new test at this step — Task 1 is pure markup with no logic of its own. Proceed directly to implementation. Task 4's e2e test (`page.click("#open-create-escalation")` etc.) is what will fail against markup that doesn't yet exist if run now; verification for this task is the manual DOM check below, not a new automated test.

- [ ] **Implement**

Add inside `#view-escalations` (after the existing `#escalation-edit-form`, before the closing `</section>`):

```html
<button type="button" id="open-create-escalation">New Escalation</button>
<section id="create-escalation" hidden>
  <h2>New Escalation</h2>
  <form id="create-escalation-form" novalidate>
    <label>Account ID <input id="create-escalation-account_id" name="account_id" required /></label>
    <label>Summary <input id="create-escalation-summary" name="summary" required /></label>
    <label>Incident number <input id="create-escalation-incident_number" name="incident_number" /></label>
    <label>Owner <input id="create-escalation-owner" name="owner" /></label>
    <button type="submit">Create Escalation</button>
    <button id="cancel-create-escalation" type="button">Cancel</button>
    <p id="create-escalation-error" role="alert" hidden></p>
  </form>
</section>
```

Follow the existing `#create-incident` id-naming convention (`create-<field>`) but prefixed `create-escalation-<field>` since `create-account_id` etc. are already taken by the incident form on the same page.

`novalidate` on the form is required, not decorative: BEH-8 mandates a custom inline validation message, but the browser's native constraint validation (triggered by `required`) intercepts `submit` before any JS handler runs, so without `novalidate` the custom message in Task 3 is unreachable in a real browser (`required` is kept on the inputs for semantic/accessibility value; only native submit-blocking is disabled). Discovered during Task 3/4's real-browser verification — the original draft omitted this and the e2e RED phase caught it.

- [ ] **Verify**

Open `static/index.html` in a browser (or via the `run` skill) and confirm the Escalations view shows the "New Escalation" button and that clicking it has no effect yet (no JS wired — expected at this stage).

- [ ] **Commit**

Branch: `feat/agent-ui/create-escalation`

```bash
git add static/index.html
git commit -m "feat(agent-ui): add New Escalation form markup"
```

---

### Task 2: Create-escalation validation & payload logic [specialist: none]

**Depends on:** Task 1
**Charter capability:** Create escalation
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Modify: `static/js/escalations-logic.js`
- Test: `tests_js/escalations-beh-6-7-create-payload.test.js`
- Test: `tests_js/escalations-beh-8-validation.test.js`

**Tests:** `tests_js/escalations-beh-6-7-create-payload.test.js`, `tests_js/escalations-beh-8-validation.test.js` — new suites (per-behavior granularity; BEH-6/BEH-7 share one payload-builder function so share one suite, BEH-8's validation function gets its own).

**Context to load:**
- `static/js/incident-logic.js:120-135` (`validateCreateIncidentForm` — required-field pattern to mirror)
- `static/js/escalations-logic.js` (full — existing module shape, UMD wrapper, existing exports)

- [ ] **Write failing test**

`tests_js/escalations-beh-6-7-create-payload.test.js`:
```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { buildEscalationCreatePayload } = require("../static/js/escalations-logic.js");

test("BEH-6: required-only fields produce a minimal payload", () => {
  const payload = buildEscalationCreatePayload({ account_id: "ACCOUNT-1001", summary: "New issue", incident_number: "", owner: "" });
  assert.deepEqual(payload, { account_id: "ACCOUNT-1001", summary: "New issue" });
});

test("BEH-7: optional fields are included when filled in", () => {
  const payload = buildEscalationCreatePayload({ account_id: "ACCOUNT-1001", summary: "New issue", incident_number: "TICKET-004417", owner: "Rui Bastos" });
  assert.deepEqual(payload, { account_id: "ACCOUNT-1001", summary: "New issue", incident_number: "TICKET-004417", owner: "Rui Bastos" });
});
```

`tests_js/escalations-beh-8-validation.test.js`:
```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const { validateCreateEscalationForm } = require("../static/js/escalations-logic.js");

test("BEH-8: missing account_id is flagged", () => {
  const { valid, errors } = validateCreateEscalationForm({ account_id: "", summary: "New issue" });
  assert.equal(valid, false);
  assert.equal(errors.account_id, "account_id is required");
});

test("BEH-8: missing summary is flagged", () => {
  const { valid, errors } = validateCreateEscalationForm({ account_id: "ACCOUNT-1001", summary: "" });
  assert.equal(valid, false);
  assert.equal(errors.summary, "summary is required");
});

test("BEH-8: both fields present is valid", () => {
  const { valid, errors } = validateCreateEscalationForm({ account_id: "ACCOUNT-1001", summary: "New issue" });
  assert.equal(valid, true);
  assert.deepEqual(errors, {});
});
```

- [ ] **Verify test fails**

Run: `node --test tests_js/escalations-beh-6-7-create-payload.test.js tests_js/escalations-beh-8-validation.test.js`
Expected: FAIL — `buildEscalationCreatePayload is not a function` / `validateCreateEscalationForm is not a function`.

- [ ] **Implement**

In `static/js/escalations-logic.js`, add before the final `return`:

```javascript
const REQUIRED_CREATE_FIELDS = ["account_id", "summary"];

function validateCreateEscalationForm(fields) {
  const errors = {};
  for (const key of REQUIRED_CREATE_FIELDS) {
    const value = fields[key];
    if (value === undefined || value === null || String(value).trim() === "") {
      errors[key] = `${key} is required`;
    }
  }
  return { valid: Object.keys(errors).length === 0, errors };
}

function buildEscalationCreatePayload(fields) {
  const payload = { account_id: fields.account_id, summary: fields.summary };
  if (fields.incident_number) payload.incident_number = fields.incident_number;
  if (fields.owner) payload.owner = fields.owner;
  return payload;
}
```

Add both to the module's `return { ... }` export list.

- [ ] **Verify test passes**

Run: `node --test tests_js/escalations-beh-6-7-create-payload.test.js tests_js/escalations-beh-8-validation.test.js`
Expected: PASS

- [ ] **Commit**

```bash
git add static/js/escalations-logic.js tests_js/escalations-beh-6-7-create-payload.test.js tests_js/escalations-beh-8-validation.test.js
git commit -m "feat(agent-ui): add create-escalation validation and payload logic"
```

---

### Task 3: Create-escalation wiring [specialist: none]

**Depends on:** Task 1, Task 2
**Charter capability:** Create escalation
**Strategy:** unit (source: fallback, confidence: high — DOM wiring is exercised end-to-end by Task 4's e2e test; this step's own verification is manual/e2e, not a new unit suite, consistent with how `incident.js`'s `onCreateIncidentSubmit` wiring has no dedicated unit test either)
**Files:**
- Modify: `static/js/escalations.js`

**Tests:** covered by `tests_e2e/test_ui_create_escalation_e2e.py` (Task 4) — this task's DOM-wiring code has no pure-function surface to unit test, matching the existing `onCreateIncidentSubmit` precedent in `incident.js`.

**Context to load:**
- `static/js/incident.js:330-368` (`onCreateIncidentSubmit`, open/cancel handlers — the wiring pattern)
- `static/js/escalations.js` (full — `renderEscalationsTable`, `loadEscalationsView`, `showEscalationsError`, reused here)

- [ ] **Write failing test**

No new unit test — see Strategy note above. Task 4's e2e test is written first (RED) against this task's not-yet-implemented wiring: write `tests_e2e/test_ui_create_escalation_e2e.py` now (see Task 4) and run it to confirm it fails against the current `escalations.js` before implementing this task.

- [ ] **Implement**

In `static/js/escalations.js`, add:

```javascript
document.getElementById("open-create-escalation").addEventListener("click", () => {
  document.getElementById("create-escalation").hidden = false;
});

document.getElementById("cancel-create-escalation").addEventListener("click", (event) => {
  event.preventDefault();
  document.getElementById("create-escalation-form").reset();
  document.getElementById("create-escalation-error").hidden = true;
  document.getElementById("create-escalation").hidden = true;
});

async function onCreateEscalationSubmit(event) {
  event.preventDefault();
  const form = event.target;
  const fields = {
    account_id: form.account_id.value,
    summary: form.summary.value,
    incident_number: form.incident_number.value,
    owner: form.owner.value,
  };
  const errorEl = document.getElementById("create-escalation-error");
  const { valid, errors } = EscalationsLogic.validateCreateEscalationForm(fields);
  if (!valid) {
    errorEl.textContent = Object.values(errors)[0];
    errorEl.hidden = false;
    return;
  }
  errorEl.hidden = true;
  const payload = EscalationsLogic.buildEscalationCreatePayload(fields);
  try {
    const resp = await fetch("/escalations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) throw { status: resp.status };
    const created = await resp.json();
    escalationsCache = [created, ...escalationsCache]; // BEH-6/7: prepend, no reload
    renderEscalationsTable(escalationsCache); // reuses existing textContent-only render path (SUG-1)
    form.reset();
    document.getElementById("create-escalation").hidden = true;
  } catch (err) {
    // BEH-9: form values are retained (no form.reset(), section stays open) and the error is shown
    errorEl.textContent = UiErrors.formatApiError("Creating escalation", err);
    errorEl.hidden = false;
  }
}

document.getElementById("create-escalation-form").addEventListener("submit", onCreateEscalationSubmit);
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_ui_create_escalation_e2e.py`
Expected: PASS (all three scenarios from Task 4: BEH-6/7 success, BEH-8 client-side validation, BEH-9 network-failure retention).

- [ ] **Commit**

```bash
git add static/js/escalations.js
git commit -m "feat(agent-ui): wire New Escalation form to POST /escalations"
```

---

### Task 4: Create-escalation e2e coverage [specialist: none]

**Depends on:** Task 3
**Charter capability:** Create escalation
**Strategy:** e2e (source: detected, confidence: high — path matches `tests_e2e/**`)
**Files:**
- Create: `tests_e2e/test_ui_create_escalation_e2e.py`

**Tests:** `tests_e2e/test_ui_create_escalation_e2e.py` (this task's own file — addresses review finding CON-1)

**Context to load:**
- `tests_e2e/test_ui_create_incident_e2e.py` (structural pattern: `page`/`ui_app_server` fixtures, `page.fill`/`page.click`/`page.wait_for_selector`)
- `tests_e2e/conftest.py` (fixture definitions — read only, not modified)

- [ ] **Write failing test**

```python
"""Real-browser create-escalation e2e coverage (BEH-6, BEH-7, BEH-8, BEH-9)."""
import uuid


def test_create_escalation_form_prepends_new_row(page, ui_app_server):
    page.goto(ui_app_server)
    page.click("#nav-escalations")
    page.wait_for_selector("#view-escalations:not([hidden])")

    summary = f"e2e-created escalation {uuid.uuid4()}"
    page.click("#open-create-escalation")
    page.wait_for_selector("#create-escalation:not([hidden])")

    page.fill("#create-escalation-account_id", "ACCOUNT-1001")
    page.fill("#create-escalation-summary", summary)
    page.click("#create-escalation-form button[type=submit]")

    page.wait_for_selector("#create-escalation", state="hidden")
    first_row_summary = page.locator("#escalations-table tbody tr").first.locator("td").nth(2).inner_text()
    assert first_row_summary == summary


def test_create_escalation_missing_required_field_shows_inline_error(page, ui_app_server):
    # BEH-8: client-side validation blocks the request entirely — no fetch is ever made.
    page.goto(ui_app_server)
    page.click("#nav-escalations")
    page.wait_for_selector("#view-escalations:not([hidden])")
    page.click("#open-create-escalation")
    page.wait_for_selector("#create-escalation:not([hidden])")

    page.fill("#create-escalation-summary", "missing account id")
    page.click("#create-escalation-form button[type=submit]")

    page.wait_for_selector("#create-escalation-error:not([hidden])")
    error = page.locator("#create-escalation-error")
    assert "account_id" in error.inner_text()
    # form stays open and retains the entered value
    assert page.input_value("#create-escalation-summary") == "missing account id"


def test_create_escalation_network_failure_shows_error_and_retains_form(page, ui_app_server):
    # BEH-9: a genuine POST /escalations failure — a real aborted network request at the
    # browser's network layer (page.route(...).abort), not a mocked fetch, matching
    # tests_e2e/test_ui_error_path_e2e.py's precedent. Client-side validation passes here;
    # the request is actually sent and then fails.
    page.goto(ui_app_server)
    page.click("#nav-escalations")
    page.wait_for_selector("#view-escalations:not([hidden])")
    page.click("#open-create-escalation")
    page.wait_for_selector("#create-escalation:not([hidden])")

    page.route("**/escalations", lambda route: route.abort("failed"))

    page.fill("#create-escalation-account_id", "ACCOUNT-1001")
    page.fill("#create-escalation-summary", "will fail to save")
    page.click("#create-escalation-form button[type=submit]")

    page.wait_for_selector("#create-escalation-error:not([hidden])")
    error = page.locator("#create-escalation-error")
    assert error.inner_text().strip() != ""
    # the form stays open (not hidden) and the entered values are retained, not cleared
    assert page.locator("#create-escalation").is_visible()
    assert page.input_value("#create-escalation-account_id") == "ACCOUNT-1001"
    assert page.input_value("#create-escalation-summary") == "will fail to save"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_ui_create_escalation_e2e.py`
Expected: FAIL — `#open-create-escalation` not found (Task 1/2/3 not yet implemented, if run before them; if run after Tasks 1-3 as TDD strictly requires, write this file *before* Task 3's implementation per the note in Task 3, then implement Task 3, then return here to confirm PASS).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_ui_create_escalation_e2e.py`
Expected: PASS — all three scenarios green after Task 3 is implemented.

- [ ] **Commit**

```bash
git add tests_e2e/test_ui_create_escalation_e2e.py
git commit -m "test(agent-ui): add e2e coverage for New Escalation form"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are recorded in the validation report (`.validate.md`), not in this plan.

- Tests pass: `python3 -m pytest -q` (full suite, including `tests_e2e/test_ui_create_escalation_e2e.py`) and `node --test tests_js/` (all JS unit suites)
- Lint passes: `ruff check .`
- All acceptance criteria from `escalations-directory-nav-rev-3-create-escalation.spec.md` satisfied
