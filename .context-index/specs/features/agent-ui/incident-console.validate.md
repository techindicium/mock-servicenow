---
spec: .context-index/specs/features/agent-ui/incident-console.spec.md
spec-revision: 3
date: 2026-09-09
tier: quick
overall_status: PASS
---

# Validation Report: Incident console — revision 3 (Related Escalation panel, BEH-10)

> **Date:** 2026-09-09
> **Spec:** .context-index/specs/features/agent-ui/incident-console.spec.md (revision 3)
> **Rigor tier:** quick (risk_level: low → `policies.low.validate_mode: quick`)
> **Overall Status:** PASS
> **Scope:** BEH-10 only — BEH-1 through BEH-9 were already validated at revision 2 (see prior
> `.validate.md` history in git) and are unchanged.

---

## Check 1: Quality Gates — PASS
- test (`python3 -m pytest -q`): PASS — 187 passed
- test-js (`node --test tests_js/**/*.test.js`): PASS — 82 passed (includes this revision's
  `tests_js/beh-10-related-escalation.test.js`, 7/7)
- lint (`ruff check .`): PASS
- e2e-smoke (`python3 -m pytest -q tests_e2e/`, severity warning): PASS — 52 passed, 1 skipped
  (includes `tests_e2e/test_ui_related_escalation_e2e.py`)

## Check 2 + Check 4 (quick-tier synthesized compliance check), BEH-10 scope — PASS

- `shapeRelatedEscalation` (`static/js/incident-logic.js`) and `renderRelatedEscalation`
  (`static/js/incident.js`) verified against BEH-10's contract with file:line citations: filters
  by `incident_number`, sorts matches by `number` ascending, `null` → `formatNullableField`
  placeholders ("unassigned"/"Open"), panel always renders (never omitted).
- Unit tests confirmed to exercise every required case (no-match, single match, null owner, null
  closed_at, non-null pass-through, multi-match ordering, empty/undefined input) — 7/7 pass.
- E2E test confirmed to drive the real page and assert the "No related escalation" state — the
  only branch reachable against real seed data, since every seeded Escalation has
  `incident_number: null` (verified in `app/fixtures/seed/escalations_seed.json`). This is a
  documented, deliberate scope limit, not a gap — the "match found" logic is proven exhaustively
  at the unit level instead.
- Scope expansion: all 18 `source-manifest.files` entries (including this revision's two new test
  files) confirmed committed via `git log`.
- Constitution: Principle 4 (HTTP boundary) — the new `/escalations` fetch is a real relative
  fetch, no DB access. Principle 6 (seeded discrepancies load-bearing) — `formatNullableField`
  only affects display text, never strips/corrects the underlying null. Safe-DOM standard — the
  only `innerHTML` use in `renderRelatedEscalation` is a safe `= ""` clear; all field values use
  `.textContent`.

## Check 1.5 (Source Manifest), 1.6 (Code Drift), 8 (Boundaries), 9 (Transition Gates) — SKIP
- Skipped — quick rigor tier.

## Check 11: Visual Verification — SKIPPED-DISABLED
- Covered instead by this repo's real-browser Playwright suite (`tests_e2e/test_ui_*.py`).

---

**Note — unplanned but verified fix bundled in this branch's history:** while implementing the
*next* spec (`dashboard.spec.md`), a real SQLite thread-safety bug in `app/db.py` was found and
fixed (a shared `sqlite3.Connection` across FastAPI's threadpool with no locking, causing
intermittent 500s under genuine concurrent load). That fix is scoped to `dashboard.spec.md`'s own
validation, not this spec's — noted here only because it landed in the same merged history and
this spec's own gate run (which passed) incidentally exercises the fixed code path.

**Summary:** 2 passed (Check 1, synthesized Check 2+4), 4 skipped (quick tier: 1.5/1.6/8/9),
1 skipped-disabled (Check 11). 0 failed.
