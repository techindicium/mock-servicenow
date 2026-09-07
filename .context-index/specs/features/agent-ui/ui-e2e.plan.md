<!-- partial_schema: plan@1 -->

# Implementation Plan: End-to-end UI test suite (real browser)

> **Methodology:** adev
> **Charter:** .context-index/specs/features/agent-ui/charter.md
> **Spec:** .context-index/specs/features/agent-ui/ui-e2e.spec.md
> **Review:** PASS (2026-09-07) — SA-1 (suggestion): filter-interaction behavior is left to the
> non-e2e test layer this milestone (`incident-console.spec.md` BEH-2 owns it); no action needed.
> CON-1 (suggestion): the claim that the reused itsm-api api-e2e fixture also serves `static/`
> isn't yet traceable to that spec's own contract — this plan's Architecture section below notes
> the static-serving dependency explicitly, satisfying CON-1 without a spec-text change.
> **Platform:** FastAPI (uvicorn) + vanilla JS static frontend (assumed — mirrors `mock-jira`'s
> `kanban-ui` shape per this repo's constitution "Patterns to Follow"), Python 3.11, Playwright
> (Chromium, sync API), pytest.

**Goal:** Add a real-browser end-to-end test suite that drives agent-ui's actual served page — a
real Chromium instance clicking, filling forms, and reading the rendered DOM — over the same real
`itsm-api` server process the sibling `api-e2e` suite already starts, never calling any UI
JS module's functions directly.

**Architecture:** Tests land in the same `tests_e2e/` directory `api-e2e` already created
(`tests_e2e/servers.py`, `tests_e2e/conftest.py`, `tests_e2e/mcp_client.py`, and the mcp-e2e /
api-e2e suites already present there), reusing `start_itsm_api(tmp_path)` unchanged — no changes
to `tests_e2e/servers.py`. A new `tests_e2e/browser.py` mirrors that module's shape for the
browser side, copied directly from `mock-jira`'s validated `tests_e2e/browser.py` pattern:
`launch_chromium()` wraps `playwright.sync_api.sync_playwright().chromium.launch()` in a context
manager, translating Playwright's own "binary not installed" error into a clearly-named
`E2EBrowserNotInstalled` exception (spec's `E2E_BROWSER_NOT_INSTALLED`). `tests_e2e/conftest.py`
gains three fixtures: session-scoped `browser` (one real Chromium instance for the whole run),
function-scoped `page` (a fresh browser context/tab per test), and function-scoped `ui_app_server`
— deliberately its own fixture, not the existing session-scoped `server` fixture the api-e2e/
mcp-e2e suites share. `server` accumulates every Incident/WorkNote/Escalation those suites create
across the whole session; BEH-1's "seeded Incidents visible" and BEH-6's "at least one ownerless
Escalation" assertions need a starting state whose composition this suite controls, and BEH-3/
BEH-4's reload-persistence checks must not be confused by another suite's concurrent writes if
tests ever run interleaved. `ui_app_server` starts its own fresh subprocess per test (via pytest's
function-scoped `tmp_path`), giving every ui-e2e test the same deterministic freshly-seeded
starting state, independent of whatever `api-e2e`/`mcp-e2e`'s tests have done in the same run —
this mirrors `mock-jira`'s own `ui_board_server` fixture and directly answers that plan's
precedent (test-isolation clarity, matching this repo's own api-e2e review's spirit).

**Root-URL / static-serving note (resolves review note CON-1):** `app/main.py` today defines
`GET /` as a JSON health check (`{"status": "ok", ...}`) that `tests_e2e/servers.py`'s
`start_itsm_api` polls to detect a healthy process — see `app/main.py`'s own comment: "api-e2e
fixture polls this route to detect a healthy process startup." BEH-1 of this spec requires that
same root URL to render the Incidents view instead once agent-ui exists. This plan does not
change `app/main.py` — that is `incident-console.plan.md`'s responsibility (the "static shell"
task in its own Actionable Task Map), which per this spec's own Preconditions must land before
this plan's tests can pass. The two are compatible without any fixture change: FastAPI's
`StaticFiles(html=True)` mount at `/` (the anticipated approach, matching `mock-jira`'s own
`app.mount("/", StaticFiles(directory="static", html=True), name="static")`) serves
`static/index.html` with a `200` status for `GET /`, which is all `start_itsm_api`'s health poll
checks (status code, not body) — so `tests_e2e/servers.py` needs no change either way. At the time
this plan was written, neither `incident-console.plan.md` nor `escalations-directory-nav.plan.md`
exists yet (both sibling specs are `status: review-passed` but unplanned); this plan proceeds on
that documented assumption. If the sibling implementation takes a different shape (e.g. mounting
static assets under a `/static/` path with a separate root-serving route), the fixture in Task 1
of this plan still works unmodified — only the element selectors in Tasks 2-6 would need
adjusting, which is normal drift to expect between planning and implementation for concurrently
authored sibling UIs.

**Selector-naming note:** No agent-ui HTML/JS exists yet (unlike `mock-jira`'s `kanban-ui`, which
was already implemented when its own `ui-e2e.plan.md` was written and could cite exact element
ids). This plan's test bodies use anticipated element ids/selectors derived from the charter's and
specs' own vocabulary (e.g. `#incidents-view`, `#incident-record`, `#add-work-note-form`), noted
per-task below. Confirm exact selectors against whatever `incident-console.plan.md` and
`escalations-directory-nav.plan.md` actually land before running each task's "Write failing test"
step — adjust locators, not behavioral intent, exactly as `api-e2e.plan.md` did for itsm-api's own
endpoint paths when itsm-api's sibling specs were still unplanned.

Playwright itself is a new dependency, added to the existing `requirements-e2e.txt` (currently
`-r requirements.txt` only), matching `mock-jira`'s precedent of isolating e2e-only dependencies
out of `requirements.txt`. The one-time `playwright install chromium` step is documented in
README.md and the constitution's Commands section (propagated to `CLAUDE.md` via a subsequent
`/adev:sync`, not by this plan directly — `/adev:sync` is a separate skill invocation). No new
gate is wired — these tests land inside `tests_e2e/`, which the existing `e2e-smoke` gate
(`tier: e2e`, already `severity: warning`, already wired in `governance/gates.yaml`) already runs.

---

## File Structure

**Create:**
- `tests_e2e/browser.py` — `launch_chromium()` context manager and `E2EBrowserNotInstalled`
  exception; the browser-side counterpart to `tests_e2e/servers.py`.
- `tests_e2e/test_browser_fixture.py` — tests the `launch_chromium()` contract itself (a working
  browser; the wrapped `E2EBrowserNotInstalled` error path), matching `api-e2e`'s
  `test_server_fixture.py` convention.
- `tests_e2e/test_ui_incident_render_e2e.py` — BEH-1, BEH-2.
- `tests_e2e/test_ui_work_note_e2e.py` — BEH-3.
- `tests_e2e/test_ui_edit_incident_e2e.py` — BEH-4, including the resolve-with-breach case.
- `tests_e2e/test_ui_create_incident_e2e.py` — BEH-5.
- `tests_e2e/test_ui_escalations_directory_e2e.py` — BEH-6, BEH-7 (grouped per this spec's own
  Actionable Task Map row "Escalations/Directory view e2e tests").
- `tests_e2e/test_ui_error_path_e2e.py` — BEH-8, `E2E_UI_FETCH_FAILED`.

**Modify:**
- `requirements-e2e.txt` — add `playwright` (currently only `-r requirements.txt`).
- `tests_e2e/conftest.py` — add `browser`, `page`, `ui_app_server` fixtures. Existing `server`,
  `anyio_backend`, `mcp_dual_server`, `mcp_server_unreachable` fixtures are untouched.
- `README.md` — add a "Running the UI end-to-end test suite" section.
- `.context-index/constitution.md` — add the one-time `playwright install chromium` setup step to
  the Commands section, alongside the existing `pip install -r requirements.txt` line.

**Reference (read, do not modify) — anticipated paths, not yet created; confirm exact names
against whatever the sibling agent-ui plans actually land before writing each task's test:**
- `tests_e2e/servers.py` — `start_itsm_api(tmp_path)`, reused unchanged (full read already done
  during planning; no further changes anticipated).
- `tests_e2e/conftest.py` — existing `server` fixture and its own docstring's rationale (tests
  needing a truly fresh seed call `start_itsm_api` directly rather than the shared fixture) — the
  same rationale this plan's own `ui_app_server` fixture follows.
- `app/main.py` — root route change from JSON health to static-serving (see Architecture's
  Root-URL note); `incident-console.plan.md`'s responsibility, not this plan's.
- `static/index.html` (anticipated, `incident-console.plan.md` Task 1 "Static shell") — nav rail
  item ids, view container ids, incident list/record markup, work-note timeline/form markup, SLA
  panel markup, create/edit-incident form markup.
- `static/index.html` additions from `escalations-directory-nav.plan.md` (anticipated) — nav rail
  Escalations/Directory items, escalations list/edit-form markup, directory list markup.
- `static/js/*.js` (anticipated) — fetch/render helpers and event wiring this suite exercises
  indirectly through the real DOM only, never called directly.
- `app/seed.py` — the seeded fixture data (Incidents, Escalations, ownerless rows, breached SLA
  records) this suite's assertions read facts from; already implemented (itsm-api milestone mvp).
- `requirements.txt`, `requirements-e2e.txt` (current contents) — precedent for isolating the new
  `playwright` dependency out of the fast-gate dependency set.
- `governance/gates.yaml` — existing `e2e-smoke` gate; already covers this suite's location, no
  change needed (unlike `mock-jira`'s `api-e2e.plan.md`, which had to wire it — here it is already
  wired by itsm-api's own `api-e2e.plan.md` Task 12).
- `mock-jira/.context-index/specs/features/kanban-ui/ui-e2e.plan.md` — full structural pattern
  this plan mirrors (`browser.py`, fixture design, requirements-e2e.txt convention, task shape).

---

## Context Packets

No `source-manifest.files[]` exists yet on this spec (first implementation pass; agent-ui has no
code yet). Context packets fall back to the charter Capability Map, this spec's own Preconditions/
Behaviors, the two sibling agent-ui specs' Behavioral Contracts, and `mock-jira`'s validated
`ui-e2e.plan.md` as a structural pattern reference.

### Task 1 Context
- Spec: `ui-e2e.spec.md` — Preconditions, `infra_requirements` frontmatter,
  `E2E_BROWSER_NOT_INSTALLED` Error Case row
- Charter: `charter.md` (capability: "End-to-end UI test suite")
- Source files: `tests_e2e/servers.py` (full read — the pattern `browser.py` mirrors, and the
  fixture this plan's `ui_app_server` wraps unchanged), `tests_e2e/conftest.py` (full read —
  existing `server`/`mcp_dual_server`/`mcp_server_unreachable` fixtures, not to be touched)
- Pattern: `mock-jira/.../kanban-ui/ui-e2e.plan.md` Task 1 (`browser.py`, fixture design,
  `requirements-e2e.txt` convention) — copied near-verbatim, only the app-specific title assertion
  and server-fixture name differ
- Constitution: "Fixture-backed, offline only" (no real network target; Chromium is a local binary)

### Task 2 Context
- Spec: `ui-e2e.spec.md` — BEH-1, BEH-2
- Charter: `charter.md` (capabilities: "Incident list view", "Incident record view", "SLA panel")
- Sibling spec: `incident-console.spec.md` — BEH-1 (list fields/pagination), BEH-3 (record fields,
  null handling), BEH-4 (work-note timeline render), BEH-6 (SLA panel, breach shown factually)
- Constitution: Principle 6 (resolved-with-open-breach is a fact, never hidden or flagged)

### Task 3 Context
- Spec: `ui-e2e.spec.md` — BEH-3
- Charter: `charter.md` (capability: "Work-note timeline + add form")
- Sibling spec: `incident-console.spec.md` — BEH-5 (unguarded `created_by`, no-reload timeline
  append)

### Task 4 Context
- Spec: `ui-e2e.spec.md` — BEH-4
- Charter: `charter.md` (capability: "Edit incident fields")
- Sibling spec: `incident-console.spec.md` — BEH-7 (unguarded edit, including
  resolve-with-open-breach and resolve-with-no-customer-facing-note transitions)
- Constitution: Principle 5 (no confirmation dialog, no client-side transition guard)

### Task 5 Context
- Spec: `ui-e2e.spec.md` — BEH-5
- Charter: `charter.md` (capability: "Create incident")
- Sibling spec: `incident-console.spec.md` — BEH-8 (all six required fields, navigate to new
  record on success)

### Task 6 Context
- Spec: `ui-e2e.spec.md` — BEH-6, BEH-7
- Charter: `charter.md` (capabilities: "Escalations screen", "Directory screen", "App navigation
  shell")
- Sibling spec: `escalations-directory-nav.spec.md` — BEH-1 (nav shell, view switching), BEH-2
  (ownerless Escalation rendered explicitly), BEH-4 (read-only Users/AssignmentGroups)
- Constitution: Principle 6 (ownerless Escalations are a fact, never hidden or defaulted)

### Task 7 Context
- Spec: `ui-e2e.spec.md` — BEH-8, Error Cases table (`E2E_UI_FETCH_FAILED` row)
- Charter: `charter.md` — Quality Attributes (Observability: "API errors surface to the user as a
  visible message naming what failed")
- Sibling specs: `incident-console.spec.md` BEH-9 (`UI_FETCH_FAILED`),
  `escalations-directory-nav.spec.md` BEH-5 (`UI_FETCH_FAILED`) — this spec's BEH-8 explicitly
  cross-references `incident-console.spec.md` BEH-9's visible-error contract
- Pattern: `mock-jira/.../ui-e2e.plan.md` Task 7 (route-interception via `page.route(...).abort()`)

---

## Parallelization

- Group A (sequential): Task 1
- Group B (independent): Task 2
- Group C (independent): Task 3
- Group D (independent): Task 4
- Group E (independent): Task 5
- Group F (independent): Task 6
- Group G (independent): Task 7

Groups B through G each depend only on Task 1 (the `browser`/`page`/`ui_app_server` fixtures) and
can run in parallel with each other — none touches a file another group touches.

At the whole-plan level (outside this grammar, prose only): none of Task 2 through Task 7 can be
*implemented* (its "Verify test passes" step run for real) until both `incident-console.spec.md`
and `escalations-directory-nav.spec.md` have their own plans implemented, per this spec's own
Preconditions. Task 1's fixture work has no such dependency — it can be written, verified failing/
passing, and committed independently of the sibling UIs' implementation status.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Playwright browser fixture + dependency setup | small | unit | — | 2 create, 4 modify |
| 2 | Incident list/record render e2e tests (BEH-1, BEH-2) | medium | unit | Task 1 | 1 create, 0 modify |
| 3 | Add-work-note e2e test (BEH-3) | small | unit | Task 1 | 1 create, 0 modify |
| 4 | Edit-incident e2e test (BEH-4) | medium | unit | Task 1 | 1 create, 0 modify |
| 5 | Create-incident e2e test (BEH-5) | small | unit | Task 1 | 1 create, 0 modify |
| 6 | Escalations/Directory view e2e tests (BEH-6, BEH-7) | small | unit | Task 1 | 1 create, 0 modify |
| 7 | Error-path e2e test (BEH-8) | small | unit | Task 1 | 1 create, 0 modify |

All seven tasks resolve to the `unit` strategy (source: fallback — no `test_strategy` in the
spec's frontmatter, no matching `manifest.yaml` glob rule, and no file path matches any
auto-detection heuristic in `lib/test-strategies/detection.mjs`). The Strategy Summary section is
omitted per the plan template (all-unit, backward compatible). The Test Infrastructure
Requirements section below is still included, because the spec declares `infra_requirements:` in
its frontmatter regardless of strategy.

---

## Test Infrastructure Requirements

> These requirements must be satisfied before this suite's tests can run. Missing them produces a
> clear setup error (`E2E_BROWSER_NOT_INSTALLED`), not a test failure.

### External Systems

| System | Required By | Strategy |
|--------|-------------|----------|
| Playwright Chromium browser binary | Task 1 (fixture), Tasks 2-7 (all UI e2e tests) | unit |

### Credentials / Environment Variables

None. Per the spec's `infra_requirements.systems[0].env_vars: []` — Chromium is a local binary,
not a remote system; no credentials of any kind are involved.

### Pre-Provisioned State

- [ ] `playwright` Python package installed (`pip install -r requirements-e2e.txt`)
- [ ] Chromium browser binary installed via `playwright install chromium` (one-time, per machine —
  not per test run)

### CI Configuration

No new gate — these tests land inside `tests_e2e/`, which the existing `e2e-smoke` gate
(`python3 -m pytest -q tests_e2e/`, `tier: e2e`, `severity: warning`) already runs, matching the
spec's `infra_requirements.ci_tag: "e2e"`. CI (and any local run of the `e2e-smoke` gate) must
complete the one-time `pip install -r requirements-e2e.txt && playwright install chromium` step
before invoking it — documented in README.md (Task 1).

> **Local runs:** no `.env.test` needed — there are no credentials to keep out of version control
> for this suite.

### Unresolved Requirements

None — `infra_requirements:` is spec-declared (confidence: high), so auto-detection was skipped
entirely per the plan template's precedence rule.

---

## Task Structure

> Task status lives in the spec's lifecycle event log (`plan_task` events), not in the `- [ ]`
> checkboxes below — those are authoring guides only.

### Task 1: Playwright browser fixture + dependency setup [specialist: none]

**Charter capability:** End-to-end UI test suite
**Strategy:** unit (source: fallback, confidence: high)
**Files:**
- Create: `tests_e2e/browser.py`
- Modify: `requirements-e2e.txt`
- Modify: `tests_e2e/conftest.py`
- Modify: `README.md`
- Modify: `.context-index/constitution.md`
- Test: `tests_e2e/test_browser_fixture.py`

**Tests:** `tests_e2e/test_browser_fixture.py` — new suite (per-behavior granularity: this covers
the Preconditions/`E2E_BROWSER_NOT_INSTALLED` contract of the reusable browser fixture itself, not
one of BEH-1..8).

**Context to load:**
- `tests_e2e/servers.py` (the pattern `browser.py` mirrors on the server side)
- `tests_e2e/conftest.py` (existing fixtures — do not modify their bodies)
- `requirements.txt`, `requirements-e2e.txt` (current contents)
- `mock-jira/.../tests_e2e/browser.py` (structural pattern, copied near-verbatim)

- [ ] **Write failing test**

```python
# tests_e2e/test_browser_fixture.py
import pytest

from tests_e2e.browser import E2EBrowserNotInstalled, launch_chromium


def test_launch_chromium_yields_a_working_browser(ui_app_server):
    with launch_chromium() as browser:
        page = browser.new_page()
        page.goto(ui_app_server)
        # Anticipated: incident-console.plan.md's static shell sets a real <title> on
        # the served page. Confirm the exact title text against that plan once written;
        # this assertion only needs page.title() to be non-empty and reachable for real.
        assert page.title() != ""
        page.close()


def test_launch_chromium_wraps_missing_binary_error(monkeypatch):
    from playwright.sync_api import Error as PlaywrightError

    class _FakeChromium:
        def launch(self):
            raise PlaywrightError(
                "Executable doesn't exist at .../chromium-1234/chrome-linux/chrome\n"
                "Looks like Playwright was just installed or updated.\n"
                "Please run the following command to download new browsers:\n"
                "    playwright install"
            )

    class _FakePlaywrightContext:
        chromium = _FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    monkeypatch.setattr(
        "tests_e2e.browser.sync_playwright", lambda: _FakePlaywrightContext()
    )

    with pytest.raises(E2EBrowserNotInstalled) as exc_info:
        with launch_chromium():
            pass  # pragma: no cover - should never be reached

    assert "playwright install chromium" in str(exc_info.value)
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_browser_fixture.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'tests_e2e.browser'` for both tests, and
`fixture 'ui_app_server' not found` once `browser.py` exists but `conftest.py` hasn't been updated
yet.

- [ ] **Implement**

```txt
# requirements-e2e.txt
-r requirements.txt
playwright
```

```python
# tests_e2e/browser.py
"""Reusable real-browser-process fixture for e2e suites.

Launches a real Chromium browser via Playwright's sync API (never headless-mocked, always a real
rendering engine) so ui-e2e's suite drives the actual served page — real clicks, real form fills —
never a UI JS module's functions directly. Wraps Playwright's own browser-launch failure (binary
not installed) into a clearly-named exception per ui-e2e.spec.md's E2E_BROWSER_NOT_INSTALLED
error case.

Modeled directly on mock-jira's tests_e2e/browser.py::launch_chromium.
"""
import contextlib
from collections.abc import Iterator

from playwright.sync_api import Browser, Error as PlaywrightError, sync_playwright


class E2EBrowserNotInstalled(RuntimeError):
    """Raised when Playwright's Chromium binary is not installed locally."""


@contextlib.contextmanager
def launch_chromium() -> Iterator[Browser]:
    """Launch a real headless Chromium browser; yield it. Closes it (and Playwright) on exit.

    Raises:
        E2EBrowserNotInstalled: Chromium's binary is missing locally. The message names the
            remedy (`playwright install chromium`) per ui-e2e.spec.md's E2E_BROWSER_NOT_INSTALLED
            error case.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError as exc:
            raise E2EBrowserNotInstalled(
                "Playwright's Chromium binary is not installed. Run `playwright install "
                f"chromium` once, then re-run this suite. Original error: {exc}"
            ) from exc
        try:
            yield browser
        finally:
            browser.close()
```

Append to `tests_e2e/conftest.py` (existing `server`, `anyio_backend`, `mcp_dual_server`,
`mcp_server_unreachable` fixtures stay exactly as-is):

```python
from tests_e2e.browser import launch_chromium


@pytest.fixture(scope="session")
def browser():
    """Session-scoped real Chromium browser, shared across all ui-e2e tests."""
    with launch_chromium() as browser:
        yield browser


@pytest.fixture
def page(browser):
    """Function-scoped browser context/tab — a fresh, isolated page per test."""
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def ui_app_server(tmp_path_factory) -> str:
    """Function-scoped real server, isolated from the shared session-scoped `server` fixture.

    Deliberately NOT `server` above: BEH-1's default-view assertion and BEH-6's ownerless-row
    assertion need a starting state this suite controls, and BEH-3/BEH-4's reload-persistence
    checks must not be confused by another suite's concurrent writes if tests ever run
    interleaved. A fresh function-scoped server (matching mock-jira's `ui_board_server` precedent)
    keeps each ui-e2e test's seeded starting state deterministic and independent of api-e2e's/
    mcp-e2e's tests in the same run.
    """
    tmp_path = tmp_path_factory.mktemp("ui-e2e")
    with start_itsm_api(tmp_path) as base_url:
        yield base_url
```

Add a "Running the UI end-to-end test suite" section to `README.md`, and a matching one-time setup
line to `.context-index/constitution.md`'s Commands section (next to `pip install -r
requirements.txt`; propagate to `CLAUDE.md` via a subsequent `/adev:sync` run, not part of this
task):

```markdown
## Running the UI end-to-end test suite

The agent-ui end-to-end suite drives a real Chromium browser (via Playwright) against a real
`itsm-api` server process. One-time local setup:

\`\`\`bash
pip install -r requirements-e2e.txt
playwright install chromium
\`\`\`

Then run it (already covered by the `e2e-smoke` gate, which runs all of `tests_e2e/`):

\`\`\`bash
python3 -m pytest -q tests_e2e/
\`\`\`
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_browser_fixture.py`
Expected: PASS

- [ ] **Commit**

Branch (if not already created): `feat/agent-ui/e2e-testing`

```bash
git add tests_e2e/browser.py requirements-e2e.txt tests_e2e/conftest.py \
  tests_e2e/test_browser_fixture.py README.md .context-index/constitution.md
git commit -m "feat(agent-ui): add reusable real-browser e2e fixture and Playwright setup"
```

### Task 2: Incident list/record render e2e tests [specialist: none]

**Charter capability:** Incident list view, Incident record view, SLA panel
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_ui_incident_render_e2e.py`

**Tests:** `tests_e2e/test_ui_incident_render_e2e.py` — new suite (BEH-1, BEH-2).

**Context to load:**
- `incident-console.spec.md` BEH-1, BEH-3, BEH-4, BEH-6 (field/timeline/SLA rendering contract)
- Anticipated selectors (confirm against `incident-console.plan.md` once written): `#incidents-view`
  default-active view container, `#incident-list .incident-row[data-number]` list rows,
  `#incident-record` record view, `#work-note-list .work-note` timeline entries, `#sla-panel
  .sla-row[data-sla-definition]` SLA rows with a `data-breached="true"` attribute (or equivalent
  visible marker) on breached rows.

- [ ] **Write failing test**

```python
# tests_e2e/test_ui_incident_render_e2e.py
def test_incidents_view_renders_by_default_with_seeded_list(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incidents-view:not([hidden])")

    # Real DOM only — never a mocked fetch response.
    assert page.locator("#incident-list .incident-row").count() > 0


def test_opening_incident_renders_fields_work_notes_and_sla_panel(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incidents-view:not([hidden])")

    page.locator("#incident-list .incident-row").first.click()
    page.wait_for_selector("#incident-record:not([hidden])")

    assert page.locator("#incident-record [data-field='number']").count() == 1
    assert page.locator("#incident-record [data-field='short_description']").count() == 1
    # Work-note timeline and SLA panel both render as part of the record view.
    page.wait_for_selector("#work-note-list")
    page.wait_for_selector("#sla-panel")


def test_resolved_incident_with_breached_first_response_renders_as_fact(page, ui_app_server):
    # BEH-2: find a resolved/closed Incident whose first_response TaskSla has_breached is
    # true, by walking the real rendered list/record views rather than querying the API
    # directly — everything this test reads comes from the DOM.
    page.goto(ui_app_server)
    page.wait_for_selector("#incidents-view:not([hidden])")

    page.select_option("#incident-filter-state", "resolved")
    page.wait_for_selector("#incident-list .incident-row")

    found_breach = False
    rows = page.locator("#incident-list .incident-row")
    for i in range(rows.count()):
        rows.nth(i).click()
        page.wait_for_selector("#incident-record:not([hidden])")
        breached = page.locator(
            "#sla-panel .sla-row[data-sla-definition='first_response'][data-breached='true']"
        )
        if breached.count() > 0:
            found_breach = True
            # No error/warning chrome the DOM would reveal as blocking the render.
            assert page.locator("#incident-record .fatal-error").count() == 0
            break
        page.go_back()
        page.wait_for_selector("#incidents-view:not([hidden])")

    assert found_breach, (
        "expected at least one resolved Incident with a breached first_response TaskSla "
        "among the seeded, filtered rows — a load-bearing seeded discrepancy, not an error state"
    )
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_ui_incident_render_e2e.py`
Expected: FAIL — `fixture 'page' not found` / `fixture 'ui_app_server' not found` until Task 1
lands; a selector-not-found timeout once Task 1 exists but `incident-console.spec.md`'s
implementation does not yet exist. Confirm the exact expected-FAIL symptom against the current
state of the sibling plan at implementation time; if `incident-console` is already implemented and
passing by then, this test is expected to go straight to PASS — document that plainly rather than
forcing an artificial RED step, per this spec's own nature as a suite validating already-built
behavior.

- [ ] **Implement**

No production code changes expected — list/record/SLA-panel rendering is
`incident-console.spec.md`'s responsibility (BEH-1, BEH-3, BEH-4, BEH-6). This task's own
deliverable is the test file; it goes green once Task 1's fixtures and the sibling implementation
are both in place. Adjust the anticipated selectors above to whatever `incident-console.plan.md`
actually names, without changing the behavioral assertions themselves.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_ui_incident_render_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_ui_incident_render_e2e.py
git commit -m "test(agent-ui): add real-browser incident list/record render e2e coverage (BEH-1, BEH-2)"
```

### Task 3: Add-work-note e2e test [specialist: none]

**Charter capability:** Work-note timeline + add form
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_ui_work_note_e2e.py`

**Tests:** `tests_e2e/test_ui_work_note_e2e.py` — new suite (BEH-3).

**Context to load:**
- `incident-console.spec.md` BEH-5 (unguarded `created_by`, no-reload timeline append)
- Anticipated selectors: `#add-work-note-form`, fields `#work-note-created-by`,
  `#work-note-type`, `#work-note-body`.

- [ ] **Write failing test**

```python
# tests_e2e/test_ui_work_note_e2e.py
import uuid


def test_add_work_note_appears_in_timeline_and_survives_reload(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incidents-view:not([hidden])")
    page.locator("#incident-list .incident-row").first.click()
    page.wait_for_selector("#incident-record:not([hidden])")

    note_body = f"e2e note {uuid.uuid4()}"
    page.fill("#work-note-created-by", "assist")
    page.select_option("#work-note-type", "comment")
    page.fill("#work-note-body", note_body)
    page.click("#add-work-note-form button[type=submit]")

    # No page reload — the new note is visible immediately.
    page.wait_for_selector(f'#work-note-list .work-note:has-text("{note_body}")')

    # BEH-3: verified by reloading the page in the same real browser.
    number = page.locator("#incident-record [data-field='number']").inner_text()
    page.reload()
    page.wait_for_selector("#incidents-view:not([hidden])")
    page.locator(f'#incident-list .incident-row:has-text("{number}")').first.click()
    page.wait_for_selector("#incident-record:not([hidden])")
    page.wait_for_selector(f'#work-note-list .work-note:has-text("{note_body}")')
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_ui_work_note_e2e.py`
Expected: FAIL — `fixture 'page' not found` / `fixture 'ui_app_server' not found` until Task 1
lands, or a selector timeout before `incident-console`'s add-work-note form exists. If that
sibling work is already implemented and passing by the time this task runs, expect PASS directly
— document plainly rather than forcing an artificial RED step.

- [ ] **Implement**

No production code changes expected — the add-work-note form and its no-reload timeline append are
`incident-console.spec.md`'s responsibility (BEH-5).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_ui_work_note_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_ui_work_note_e2e.py
git commit -m "test(agent-ui): add real-browser add-work-note e2e coverage (BEH-3)"
```

### Task 4: Edit-incident e2e test [specialist: none]

**Charter capability:** Edit incident fields
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_ui_edit_incident_e2e.py`

**Tests:** `tests_e2e/test_ui_edit_incident_e2e.py` — new suite (BEH-4, including the
resolve-with-breach case).

**Context to load:**
- `incident-console.spec.md` BEH-7 (unguarded edit, including resolve-with-open-breach)
- Constitution Principle 5 (no confirmation dialog, no client-side transition guard)
- Anticipated selectors: `#edit-incident-form`, fields `#incident-state`, `#incident-priority`,
  `#incident-assigned-to`, `#incident-assignment-group`.

- [ ] **Write failing test**

```python
# tests_e2e/test_ui_edit_incident_e2e.py
def test_edit_incident_state_persists_after_reload(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incidents-view:not([hidden])")
    page.locator("#incident-list .incident-row").first.click()
    page.wait_for_selector("#incident-record:not([hidden])")

    number = page.locator("#incident-record [data-field='number']").inner_text()
    page.select_option("#incident-priority", "1")
    page.click("#edit-incident-form button[type=submit]")
    page.wait_for_selector("#incident-record [data-field='priority']:has-text('1')")

    page.reload()
    page.wait_for_selector("#incidents-view:not([hidden])")
    page.locator(f'#incident-list .incident-row:has-text("{number}")').first.click()
    page.wait_for_selector("#incident-record:not([hidden])")
    assert "1" in page.locator("#incident-record [data-field='priority']").inner_text()


def test_resolve_incident_with_open_first_response_breach_saves_with_no_confirmation(
    page, ui_app_server
):
    # BEH-4: an Incident whose first_response TaskSla is breached can still be set to
    # resolved with no confirmation dialog intercepted (none exists to intercept — a
    # Playwright dialog listener that fires here would itself be a spec violation).
    page.goto(ui_app_server)
    page.wait_for_selector("#incidents-view:not([hidden])")

    breach_found = False
    page.select_option("#incident-filter-state", "new")
    rows = page.locator("#incident-list .incident-row")
    for i in range(rows.count()):
        rows.nth(i).click()
        page.wait_for_selector("#incident-record:not([hidden])")
        breached = page.locator(
            "#sla-panel .sla-row[data-sla-definition='first_response'][data-breached='true']"
        )
        if breached.count() > 0:
            breach_found = True
            number = page.locator("#incident-record [data-field='number']").inner_text()
            page.select_option("#incident-state", "resolved")
            page.click("#edit-incident-form button[type=submit]")
            page.wait_for_selector("#incident-record [data-field='state']:has-text('resolved')")

            page.reload()
            page.wait_for_selector("#incidents-view:not([hidden])")
            page.select_option("#incident-filter-state", "resolved")
            page.locator(f'#incident-list .incident-row:has-text("{number}")').first.click()
            page.wait_for_selector("#incident-record:not([hidden])")
            assert "resolved" in page.locator("#incident-record [data-field='state']").inner_text()
            break
        page.go_back()
        page.wait_for_selector("#incidents-view:not([hidden])")

    assert breach_found, (
        "expected at least one un-resolved seeded Incident with a breached first_response "
        "TaskSla to exercise the resolve-with-open-breach transition"
    )
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_ui_edit_incident_e2e.py`
Expected: FAIL — `fixture 'page' not found` / `fixture 'ui_app_server' not found` until Task 1
lands, or a selector timeout before `incident-console`'s edit form exists. If already implemented
and passing by then, expect PASS directly — document plainly.

- [ ] **Implement**

No production code changes expected — unguarded field editing, including the resolve-with-breach
transition, is `incident-console.spec.md`'s responsibility (BEH-7). If a confirmation dialog or a
client-side transition guard is found to exist, that is a constitutional violation
(Principle 5) to raise against `incident-console`'s implementation, never something this test
should be loosened to tolerate.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_ui_edit_incident_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_ui_edit_incident_e2e.py
git commit -m "test(agent-ui): add real-browser edit-incident e2e coverage (BEH-4, resolve-with-breach)"
```

### Task 5: Create-incident e2e test [specialist: none]

**Charter capability:** Create incident
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_ui_create_incident_e2e.py`

**Tests:** `tests_e2e/test_ui_create_incident_e2e.py` — new suite (BEH-5).

**Context to load:**
- `incident-console.spec.md` BEH-8 (all six required fields, navigate to new record on success)
- Anticipated selectors: `#create-incident-form`, fields `#incident-account-id`,
  `#incident-category`, `#incident-short-description`, `#incident-description`,
  `#incident-create-state`, `#incident-create-priority`.

- [ ] **Write failing test**

```python
# tests_e2e/test_ui_create_incident_e2e.py
import uuid


def test_create_incident_form_navigates_to_new_record(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incidents-view:not([hidden])")

    short_description = f"e2e-created incident {uuid.uuid4()}"
    page.click("#open-create-incident")
    page.fill("#incident-account-id", "ACCOUNT-1001")
    page.select_option("#incident-category", "network")
    page.fill("#incident-short-description", short_description)
    page.fill("#incident-description", "created by the ui e2e suite")
    page.select_option("#incident-create-state", "new")
    page.select_option("#incident-create-priority", "3")
    page.click("#create-incident-form button[type=submit]")

    page.wait_for_selector("#incident-record:not([hidden])")
    assert short_description in page.locator(
        "#incident-record [data-field='short_description']"
    ).inner_text()
    assert "ACCOUNT-1001" in page.locator(
        "#incident-record [data-field='account_id']"
    ).inner_text()
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_ui_create_incident_e2e.py`
Expected: FAIL — `fixture 'page' not found` / `fixture 'ui_app_server' not found` until Task 1
lands, or a selector timeout before `incident-console`'s create form exists. If already
implemented and passing by then, expect PASS directly — document plainly.

- [ ] **Implement**

No production code changes expected — the create-incident form and its post-success navigation are
`incident-console.spec.md`'s responsibility (BEH-8).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_ui_create_incident_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_ui_create_incident_e2e.py
git commit -m "test(agent-ui): add real-browser create-incident e2e coverage (BEH-5)"
```

### Task 6: Escalations/Directory view e2e tests [specialist: none]

**Charter capability:** Escalations screen, Directory screen, App navigation shell
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_ui_escalations_directory_e2e.py`

**Tests:** `tests_e2e/test_ui_escalations_directory_e2e.py` — new suite (BEH-6, BEH-7; two
distinct spec behaviors covered by one task, per this spec's own Actionable Task Map grouping).

**Context to load:**
- `escalations-directory-nav.spec.md` BEH-1 (nav shell, view switching), BEH-2 (ownerless
  Escalation rendered explicitly), BEH-4 (read-only Users/AssignmentGroups)
- Anticipated selectors: nav items `#nav-incidents`, `#nav-escalations`, `#nav-directory`; view
  containers `#incidents-view`, `#escalations-view`, `#directory-view`; `#escalation-list
  .escalation-row[data-number]` with an owner cell rendering `null` as an explicit "Unassigned"
  state (never hidden/defaulted); `#user-list`, `#assignment-group-list`.

- [ ] **Write failing test**

```python
# tests_e2e/test_ui_escalations_directory_e2e.py
def test_escalations_view_renders_including_ownerless_row(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incidents-view:not([hidden])")

    page.click("#nav-escalations")
    page.wait_for_selector("#escalations-view:not([hidden])")
    assert page.locator("#incidents-view").is_hidden()

    assert page.locator("#escalation-list .escalation-row").count() > 0
    # BEH-6: an ownerless Escalation rendered as an explicit unassigned state, read
    # from the actual DOM — a seeded discrepancy, not an error the UI hides.
    ownerless = page.locator(
        "#escalation-list .escalation-row[data-owner='']"
    )
    assert ownerless.count() >= 1


def test_directory_view_renders_users_and_assignment_groups(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incidents-view:not([hidden])")

    page.click("#nav-directory")
    page.wait_for_selector("#directory-view:not([hidden])")
    assert page.locator("#escalations-view").is_hidden()
    assert page.locator("#incidents-view").is_hidden()

    assert page.locator("#user-list li").count() > 0
    assert page.locator("#assignment-group-list li").count() > 0
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_ui_escalations_directory_e2e.py`
Expected: FAIL — `fixture 'page' not found` / `fixture 'ui_app_server' not found` until Task 1
lands, or a selector timeout before `escalations-directory-nav`'s implementation exists. If
already implemented and passing by then, expect PASS directly — document plainly.

- [ ] **Implement**

No production code changes expected — the nav shell, Escalations view, and Directory view are
`escalations-directory-nav.spec.md`'s responsibility (BEH-1, BEH-2, BEH-4).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_ui_escalations_directory_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_ui_escalations_directory_e2e.py
git commit -m "test(agent-ui): add real-browser Escalations/Directory view e2e coverage (BEH-6, BEH-7)"
```

### Task 7: Error-path e2e test [specialist: none]

**Charter capability:** Incident list view (error path — cross-cutting to the whole app shell)
**Strategy:** unit (source: fallback, confidence: high)
**Depends on:** Task 1
**Files:**
- Create: `tests_e2e/test_ui_error_path_e2e.py`

**Tests:** `tests_e2e/test_ui_error_path_e2e.py` — new suite (BEH-8, `E2E_UI_FETCH_FAILED`; a
client-simulated network failure via Playwright route interception, matching `mock-jira`'s
`ui-e2e.plan.md` Task 7 precedent — a reasonable substitute for this tier, not a real server
outage).

**Context to load:**
- `incident-console.spec.md` BEH-9 (`UI_FETCH_FAILED`, the visible-error contract this spec's
  BEH-8 explicitly cross-references)
- Pattern: `mock-jira/.../ui-e2e.plan.md` Task 7 (`page.route(...).abort("failed")`)

- [ ] **Write failing test**

```python
# tests_e2e/test_ui_error_path_e2e.py
def test_network_failure_shows_visible_error_message(page, ui_app_server):
    # Simulate the real server becoming unreachable mid-load by aborting the incidents
    # fetch at the network layer — no mocked fetch, a real aborted request.
    page.route("**/incidents*", lambda route: route.abort("failed"))

    page.goto(ui_app_server)

    page.wait_for_selector("#incidents-error:not([hidden])")
    error_text = page.locator("#incidents-error").inner_text()
    assert error_text.strip() != ""
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests_e2e/test_ui_error_path_e2e.py`
Expected: FAIL — `fixture 'page' not found` / `fixture 'ui_app_server' not found` until Task 1
lands, or a selector timeout before `incident-console`'s error-banner element exists. If already
implemented and passing by then, expect PASS directly — document plainly.

- [ ] **Implement**

No production code changes expected — the fetch-failure error banner is
`incident-console.spec.md`'s responsibility (BEH-9), reused here per this spec's own
cross-reference.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests_e2e/test_ui_error_path_e2e.py`
Expected: PASS

- [ ] **Commit**

```bash
git add tests_e2e/test_ui_error_path_e2e.py
git commit -m "test(agent-ui): add real-browser network-failure e2e coverage (BEH-8, E2E_UI_FETCH_FAILED)"
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are
recorded in the validation report (`.validate.md`), not in this plan.

`governance/gates.yaml` defines the deterministic gates for this project — used here instead of
constitution Quality Gates, per plan template precedence:

| Gate | Tier | Command | Severity |
|------|------|---------|----------|
| `test` | fast | `python3 -m pytest -q` | error |
| `lint` | fast | `ruff check .` | error |
| `integration-test` | integration | *(unwired — `command: ""`)* | error (skipped, no command) |
| `e2e-smoke` | e2e | `python3 -m pytest -q tests_e2e/` | warning |

- No gate changes needed — `e2e-smoke` already runs the whole `tests_e2e/` directory (wired by
  itsm-api's own `api-e2e.plan.md` Task 12), so this suite's new files are picked up automatically.
- The `test` gate must keep passing unaffected — `pytest.ini`'s `testpaths = tests` (already in
  place from `api-e2e.plan.md` Task 11) keeps `tests_e2e/` out of the fast gate's bare-invocation
  discovery scope; this plan adds no new files under `tests/`.
- CI/local runners must complete the one-time `pip install -r requirements-e2e.txt && playwright
  install chromium` step (Task 1, documented in README.md) before `e2e-smoke` can pass; without it,
  every test in this suite fails fast with the `E2E_BROWSER_NOT_INSTALLED` message from
  `tests_e2e/browser.py`, not a silent hang.
- All eight acceptance criteria in `ui-e2e.spec.md` must be satisfied: Incidents view renders by
  default with seeded data (BEH-1), Incident record view renders fields/timeline/SLA panel
  including a resolved-with-breach case (BEH-2), a real add-work-note submission produces a
  visible timeline entry confirmed after reload (BEH-3), a real state edit including
  resolve-with-open-breach persists and is confirmed after reload (BEH-4), a real create-incident
  submission navigates to the new record (BEH-5), the Escalations view renders including an
  ownerless row (BEH-6), the Directory view renders (BEH-7), a simulated network failure shows a
  visible error in the real DOM (BEH-8), all quality gates passing, no constitutional violations.
- Both sibling agent-ui plans (`incident-console.plan.md`, `escalations-directory-nav.plan.md`)
  must be implemented before Tasks 2 through 7's "Verify test passes" steps can be run for real,
  per this spec's own Preconditions and this plan's Parallelization section.
- `e2e-smoke` stays `severity: warning` / `required: false` per its existing e2e-tier default —
  not escalated by this plan, consistent with itsm-api's `api-e2e.plan.md` precedent (first-
  generation e2e coverage for a course-fixture repo, not yet a merge blocker).
