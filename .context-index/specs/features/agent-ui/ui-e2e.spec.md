---
charter: agent-ui
status: review-passed
risk_level: low
milestone: v1.1
revision: 1
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
infra_requirements:
  systems:
    - name: "Playwright browser binary (Chromium)"
      env_vars: []
      cli_tools:
        - name: playwright
      notes: "One-time local setup: `playwright install chromium` downloads the browser binary this suite drives. No credentials, no network target beyond the real server this suite itself starts on localhost."
  ci_tag: "e2e"
---

# Live Spec: End-to-end UI test suite (real browser)

<!-- Live Spec within the agent-ui charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/agent-ui/charter.md -->

## Behavioral Contract

### Preconditions

- Both agent-ui specs (`incident-console`, `escalations-directory-nav`) are implemented.
- These tests reuse `itsm-api`'s `api-e2e` spec's real-server-process fixture — the same live
  server (bound to `127.0.0.1`, serving `static/` and the API from one process, seeded per the
  documented seed command) that the API e2e suite starts, not a separate mock or stub.
- A real browser (Playwright, Chromium) navigates to the live server's root URL and interacts
  with the actual rendered DOM — real clicks, real form fills. No test in this suite calls a
  JS module's function directly; every assertion is made against what a real browser rendered.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** a real browser loads the live server's root URL, **then** the Incidents
  view renders by default with a paginated list of seeded Incidents visible, read from the actual
  DOM, not a mocked fetch response.
- **BEH-2** — **When** a real browser opens an Incident from the list, **then** the record view
  renders that Incident's fields, its work-note timeline, and its SLA panel — including a case
  where the opened Incident has `state: resolved`/`closed` and its `first_response` TaskSla shows
  `has_breached: true`, rendered as a fact with no error/warning chrome the DOM inspection would
  reveal as blocking.
- **BEH-3** — **When** a real browser fills and submits the add-work-note form, **then** the new
  note becomes visible in the timeline without a page reload — verified by reloading the page in
  the same real browser and confirming the note is still there.
- **BEH-4** — **When** a real browser edits an Incident's `state` field on the record view and
  saves — **including setting it to `resolved` on an Incident whose `first_response` TaskSla is
  breached** — **then** the save succeeds with no confirmation dialog intercepted by the test (none
  exists to intercept), and a page reload in the same real browser confirms the new state persisted
  server-side.
- **BEH-5** — **When** a real browser fills and submits the create-incident form, **then** the
  browser navigates to the new Incident's record view showing the submitted fields.
- **BEH-6** — **When** a real browser switches to the Escalations view via the nav shell, **then**
  it shows the seeded Escalations, including at least one rendered with an explicit ownerless
  state — verified by reading the rendered DOM.
- **BEH-7** — **When** a real browser switches to the Directory view via the nav shell, **then**
  it shows the seeded SysUser and AssignmentGroup lists, read from the actual DOM.
- **BEH-8** — **When** the real server becomes unreachable mid-test (simulated via Playwright
  route interception forcing a network failure), **then** the real browser shows a visible error
  message, matching `incident-console.spec.md` BEH-9 — verified by reading the rendered DOM, not
  a mock.

### Postconditions

- Every assertion in this suite reads the real, rendered DOM (via Playwright locators) — never a
  JS module's internal state or a mocked network layer.
- The browser and the underlying live server are both torn down after the test session.

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Real server becomes unreachable mid-test (BEH-8) | Visible error message in the rendered DOM | `E2E_UI_FETCH_FAILED` |
| Playwright cannot launch the browser (binary not installed) | Test setup fails loudly naming the missing binary and the `playwright install chromium` remedy | `E2E_BROWSER_NOT_INSTALLED` |

## System Constitution Reference

- **Principle 4:** "The HTTP contract is the boundary." — Applies because this suite still only
  interacts with agent-ui through the real, served page — it never reaches past the browser into
  internal JS state or the database.
- **Principle 2:** "Fixture-backed, offline only." — Applies because the real server and browser
  this suite drives are both local-only.
- **Principle 5 / 6:** Applies directly to BEH-2/BEH-4: the unguarded resolve-with-open-breach
  transition and the factual SLA/discrepancy rendering are this suite's real-browser proof that
  the unit-level behavior actually holds end to end.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Playwright setup | Add `playwright`/`pytest-playwright` to dev dependencies (`requirements-e2e.txt`); document the one-time `playwright install chromium` step | small |
| Incident list/record render e2e tests | Real-browser tests for BEH-1, BEH-2 | medium |
| Add-work-note e2e test | Real-browser form test for BEH-3 | small |
| Edit-incident e2e test | Real-browser test for BEH-4, including the resolve-with-breach case | medium |
| Create-incident e2e test | Real-browser form test for BEH-5 | small |
| Escalations/Directory view e2e tests | Real-browser tests for BEH-6, BEH-7 | small |
| Error-path e2e test | Route-interception test for BEH-8 | small |

## Acceptance Criteria

- [ ] A real browser renders the Incidents view by default with seeded data (BEH-1)
- [ ] A real browser renders an Incident's record view, work notes, and SLA panel, including a resolved-with-breach case (BEH-2)
- [ ] A real add-work-note submission produces a visible timeline entry, confirmed after reload (BEH-3)
- [ ] A real state edit, including resolve-with-open-breach, persists and is confirmed after reload (BEH-4)
- [ ] A real create-incident submission navigates to the new record (BEH-5)
- [ ] A real browser renders the Escalations view including an ownerless row (BEH-6)
- [ ] A real browser renders the Directory view (BEH-7)
- [ ] A simulated network failure shows a visible error in the real DOM (BEH-8)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
