---
spec: .context-index/specs/features/agent-ui/incident-console.spec.md
date: 2026-09-07
tier: quick
overall_status: PASS
---

# Validation Report: Incident console (list, record view, work notes, SLA, editing, create)

> **Date:** 2026-09-07
> **Spec:** .context-index/specs/features/agent-ui/incident-console.spec.md
> **Rigor tier:** quick (risk_level: medium → `policies.medium.validate_mode: quick`)
> **Overall Status:** PASS

---

## Check 1: Quality Gates — PASS
- test (`python3 -m pytest -q`): PASS — 187 passed
- test-js (`node --test tests_js/**/*.test.js`): PASS — 67 passed (gate command fixed this run — see note below)
- lint (`ruff check .`): PASS
- e2e-smoke (`python3 -m pytest -q tests_e2e/`, severity warning): PASS — 48 passed, 1 skipped

**Note:** The `test-js` gate in `governance/gates.yaml` was found broken on this machine's Node
v25.9.0 (`node --test tests_js/` throws `MODULE_NOT_FOUND` instead of recursively discovering
tests). Fixed to `node --test "tests_js/**/*.test.js"` (Node's own internal glob resolution, no
shell needed) in commit `a4e2475`, verified directly via `execFile` (the same invocation style
the quality-gate runner uses). Source manifests for `incident-console.spec.md` and
`api-e2e.spec.md` (both track `governance/gates.yaml`) were re-stamped in commit `6491153`.

## Check 2 + Check 4 (quick-tier synthesized compliance check) — PASS

Dispatched as one synthesized subagent pass per the quick rigor tier.

**Spec compliance:** All 9 behaviors (BEH-1 through BEH-9) and the static-shell criterion verified
PASS with file:line citations against `static/js/incident.js`, `static/js/incident-logic.js`,
`app/main.py`, `tests/test_static_assets.py`, and all 9 `tests_js/beh-*.test.js` files. No loose or
unfalsifiable test assertions found. DOM/fetch wiring (not unit-tested per this repo's convention)
is covered separately by `tests_e2e/test_ui_*.py`'s real-browser Playwright suite, owned by the
sibling `ui-e2e.spec.md`.

**Scope expansion:** All 15 `source-manifest.files` entries confirmed committed via `git log`.
Extra files under `static/js/`/`tests_js/` (escalations/directory/nav files) confirmed to belong to
the sibling `escalations-directory-nav` spec, per this repo's documented cross-plan ownership
split — not a scope-expansion issue.

**Constitution compliance:**
- Principle 4 (HTTP boundary): PASS — no DB/ORM access in `static/js/`; all I/O via `fetch()`.
- Principle 5 (unguarded edit): PASS — zero `confirm(` calls; `diffIncidentFields` is a pure
  field-diff with no state-transition branching (`incident-logic.js`), including the
  resolve-with-open-breach regression test.
- Principle 6 (breach shown as fact): PASS — `shapeSlaRows` only tags a CSS class, never
  filters/hides rows.
- Safe-DOM standard: PASS — the only `innerHTML` occurrences are `= ""` clear-then-append patterns;
  all data values use `.textContent`.

## Check 1.5 (Source Manifest), 1.6 (Code Drift), 8 (Boundaries), 9 (Transition Gates) — SKIP
- Skipped — quick rigor tier.

## Check 11: Visual Verification — SKIPPED-DISABLED
- `governance/validate.yaml` disables this check project-wide. Reason (updated this session):
  `ui-e2e.spec.md`'s real-browser Playwright suite (`tests_e2e/test_ui_*.py`) already drives the
  actual served UI as part of the ordinary gate suite — a separate subagent visual-verification
  pass would duplicate that coverage, not add to it.

---

**Summary:** 2 passed (Check 1, synthesized Check 2+4), 4 skipped (quick tier: 1.5/1.6/8/9),
1 skipped-disabled (Check 11). 0 failed.

---

> **Note for users comparing with historic reports:** Checks 3, 5, 6, 7, 10, 12, and 13 have been
> relocated by `check-set-restructure.spec.md`. See `/adev:review-specs`, `/adev:hygiene`,
> `/adev:reconcile`, and `hooks/post-validate-extract-heuristics.*` respectively.
