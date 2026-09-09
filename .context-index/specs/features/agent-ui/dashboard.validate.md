---
spec: .context-index/specs/features/agent-ui/dashboard.spec.md
date: 2026-09-09
tier: quick
overall_status: PASS
---

# Validation Report: Incident dashboard (KPI tiles)

> **Date:** 2026-09-09
> **Spec:** .context-index/specs/features/agent-ui/dashboard.spec.md
> **Rigor tier:** quick (risk_level: medium → `policies.medium.validate_mode: quick`)
> **Overall Status:** PASS

---

## Check 1: Quality Gates — PASS
- test (`python3 -m pytest -q`): PASS — 187 passed
- test-js (`node --test tests_js/**/*.test.js`): PASS — 82 passed
- lint (`ruff check .`): PASS
- e2e-smoke (`python3 -m pytest -q tests_e2e/`, severity warning): PASS — 52 passed, 1 skipped;
  `tests_e2e/test_ui_dashboard_e2e.py` additionally re-run 3x in isolation, clean every time
  (confirms the bundled `app/db.py` concurrency fix holds under this spec's own 7-parallel-fetch
  load, not just the implementer's own claim).

## Check 2 + Check 4 (quick-tier synthesized compliance check) — PASS

All 5 behaviors verified with file:line citations against `static/js/dashboard-logic.js`,
`static/js/dashboard.js`, `static/js/nav.js`, and `static/index.html`:
- BEH-1: exactly 7 tiles, each sourced from a real `fetch()`'s `total` field, no client-side
  counting.
- BEH-2: `navigateToFilteredIncidents` closes any open record/create sub-view, switches to
  Incidents, populates the filter form, calls `requestSubmit()` — reuses `incident-console`'s own
  unmodified handler. E2e test confirms every resulting row is genuinely in the filtered state,
  not just that the select's value changed.
- BEH-3: the Breached SLAs tile renders as `<span>` with no click listener; e2e confirms
  `tagName === "SPAN"`.
- BEH-4: `Promise.allSettled` isolates per-tile failures; rejected tiles render an error message,
  others still render real values.
- BEH-5: the dashboard's `nav.js` branch is NOT gated by `loadedViews` (unlike escalations/
  directory) — re-fetches on every activation.

**Test integrity:** no loose matchers, no conditional skips. The e2e suite cross-checks a tile's
rendered number against an independent `httpx.get(...).json()["total"]` call rather than a
hardcoded value, and the click-through test asserts every rendered row's real `data-state`
attribute — not just that a `<select>`'s value changed — guarding against a fake/no-op filter.

**Scope expansion:** all 9 manifest files confirmed committed. The bundled `app/db.py`
thread-safety fix is correctly attributed to itsm-api's `incident-lifecycle`/`sla-records`/
`work-notes` specs' manifests, not this one — this spec's own manifest scope is honest.

**Constitution:** Principle 4 (every count is the API's own `total`, no summing), Principle 6
(breached-SLA count reported as-is, no correction), safe-DOM (only `innerHTML` use is a safe
clear), and no new write guard (the click-through path is exactly as unguarded as the filter form
it reuses) — all verified with citations.

## Check 1.5 (Source Manifest), 1.6 (Code Drift), 8 (Boundaries), 9 (Transition Gates) — SKIP
- Skipped — quick rigor tier.

## Check 11: Visual Verification — SKIPPED-DISABLED
- Covered instead by this repo's real-browser Playwright suite (`tests_e2e/test_ui_dashboard_e2e.py`).

---

**Summary:** 2 passed (Check 1, synthesized Check 2+4), 4 skipped (quick tier: 1.5/1.6/8/9),
1 skipped-disabled (Check 11). 0 failed.
