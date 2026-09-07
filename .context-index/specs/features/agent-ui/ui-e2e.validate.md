---
spec: .context-index/specs/features/agent-ui/ui-e2e.spec.md
date: 2026-09-07
tier: quick
overall_status: PASS
---

# Validation Report: End-to-end UI test suite (real browser)

> **Date:** 2026-09-07
> **Spec:** .context-index/specs/features/agent-ui/ui-e2e.spec.md
> **Rigor tier:** quick (risk_level: low → `policies.low.validate_mode: quick`)
> **Overall Status:** PASS

---

## Preflight: Infrastructure Verification — PASS
`adev preflight run --spec <path>` failed initially (`cli_tools_ok: false` — the `playwright` CLI
resolves from `.venv/bin/`, not the bare shell `PATH`). Passed once `.venv/bin` was added to `PATH`
for the check. The Chromium binary itself was confirmed installed and launchable via a direct
Playwright smoke test before any implementation work began.

## Check 1: Quality Gates — PASS
- test (`python3 -m pytest -q`): PASS — 187 passed
- test-js (`node --test tests_js/**/*.test.js`): PASS — 67 passed
- lint (`ruff check .`): PASS (using this repo's standard `ruff` 0.15.11 — see advisory below)
- e2e-smoke (`python3 -m pytest -q tests_e2e/`, severity warning): PASS — 48 passed, 1 skipped

**Advisory (non-blocking, out of this spec's scope):** `requirements.txt` pins `ruff` with no
version, and this repo's `.venv` resolves a newer `ruff` (0.16.6) than the system `ruff` (0.15.11)
normally used to run the `lint` gate — the two versions produced different results against the same
code (4 new-rule findings on the newer version, none of which are agent-ui's). No `ruff.toml`/
`pyproject.toml` `[tool.ruff]` block pins a version or rule set. Worth a follow-up to pin `ruff` in
`requirements.txt` so `lint` is deterministic regardless of which `ruff` a given shell resolves —
filed as an observation, not fixed here (out of scope for the agent-ui specs).

## Check 2 + Check 4 (quick-tier synthesized compliance check) — PASS_WITH_NOTES

Dispatched as one synthesized subagent pass per the quick rigor tier.

**Spec compliance:** All 8 behaviors (BEH-1 through BEH-8) verified PASS with file:line citations
against `tests_e2e/browser.py`, the `browser`/`page`/`ui_app_server` fixtures in `conftest.py`, and
all 6 `tests_e2e/test_ui_*.py` files plus `test_browser_fixture.py`. Every test drives a real
Chromium browser against the real served page — no `fetch` mocking, no direct JS calls, no
unfalsifiable assertions found.

**Investigated note:** The synthesized check ran `pytest -q tests_e2e/test_ui_*.py
tests_e2e/test_browser_fixture.py` (an explicit file order, not the actual configured gate) and hit
a real but narrow test-isolation issue: `test_browser_fixture.py`'s
`test_launch_chromium_yields_a_working_browser` calls `launch_chromium()` directly, which conflicts
with Playwright's sync API if the session-scoped `browser` fixture is already open from an earlier
test in the same process. I reproduced this directly, then attempted a fix (using the `browser`
fixture instead of a second direct `launch_chromium()` call) — but the fix caused a **real
regression** in the actual configured gate: it forced Playwright's session-scoped browser to spin
up during `test_browser_fixture.py` (which sorts alphabetically before the `test_mcp_*.py` files),
and its background event loop then conflicted with the `anyio`-based async MCP e2e tests, breaking
9 previously-passing tests. **Reverted the fix.** The original code is correct as written: pytest's
default alphabetical file discovery always runs `test_browser_fixture.py` (and its self-contained,
independently-opened-and-closed `launch_chromium()` calls) before any test that touches the
session-scoped `browser`/`page` fixtures, so the conflict this synthesized check surfaced never
occurs under the real, documented invocation (`python3 -m pytest -q tests_e2e/`, i.e. the
`e2e-smoke` gate) — confirmed clean 3 times in a row (48 passed, 1 skipped each time), including
after the revert. This is a real but currently-inert ordering dependency, not a defect to fix in
this pass; noting it here so a future contributor doesn't reorder or explicitly re-list these files
without being aware of it.

**Scope expansion:** All 10 manifest files confirmed committed via `git log`. The one file this
spec's implementation modified outside its own manifest — `tests_e2e/test_openapi_e2e.py`
(commit `14325cb`, itsm-api-scoped, dropping the repurposed `GET /` route from the OpenAPI
expected-paths set) — is real, small, correctly attributed to `api-e2e.spec.md`, and was already
handled as a separate commit. Not scope creep on this spec.

**Constitution compliance:**
- Principle 2 (fixture-backed, offline): PASS — `browser.py` launches only a local Chromium
  binary; no remote browser service.
- Principle 4 (HTTP boundary): PASS — `ui_app_server`/`servers.py` spawn the real app as an OS
  subprocess; no in-process `TestClient`, no Python object imports.
- Principle 5 (unguarded UI): PASS — the resolve-with-breach edit test has no
  `page.on("dialog"...)` handler; none exists to intercept.
- Principle 6 (seeded discrepancies load-bearing): PASS — the escalations e2e test hard-asserts at
  least one ownerless row, no skip/xfail.

## Check 1.5 (Source Manifest), 1.6 (Code Drift), 8 (Boundaries), 9 (Transition Gates) — SKIP
- Skipped — quick rigor tier.

## Check 11: Visual Verification — SKIPPED-DISABLED
- `governance/validate.yaml` disables this check project-wide — this spec's own suite IS the
  intended replacement mechanism.

---

**Summary:** 2 passed (Check 1, synthesized Check 2+4 with one investigated-and-resolved note),
4 skipped (quick tier: 1.5/1.6/8/9), 1 skipped-disabled (Check 11). 0 failed. Aggregate verdict
PASS (the note was investigated to a confirmed non-issue for the real gate, not left open).
