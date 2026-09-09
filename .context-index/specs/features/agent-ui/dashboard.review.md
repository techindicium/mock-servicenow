---
spec: .context-index/specs/features/agent-ui/dashboard.spec.md
spec-revision: 1
date: 2026-09-09
tier: quick
verdict: PASS_WITH_NOTES
---

# Review: Incident dashboard (KPI tiles)

Quick-tier synthesized review (structural + security + consistency, one pass).

## Verification performed

- Confirmed against `app/routers/incidents.py`/`app/routers/sla.py`: `state`, `escalated`,
  `page_size` (on `/incidents`) and `breached`, `page_size` (on `/sla`) are real query params;
  `INCIDENT_STATES` matches BEH-1's five state tiles exactly; both `IncidentPage` and
  `PaginatedTaskSla` expose `total`.
- Cross-checked BEH-2 against `incident-console.spec.md`'s real BEH-2 text — no contradiction.
- Confirmed `escalations-directory-nav.spec.md` BEH-1 still names Incidents as default view; this
  spec's Precondition explicitly preserves that.
- Charter (revision 22) Capability Map and Consumed APIs describe this exact behavior — in scope.
- Constitution Principles 4 and 6 citations both apply correctly.
- No new write surface, no new free-text rendering — security scope unchanged.

## Findings

**SA-1** — severity: warning — location: Actionable Task Map, "Tile DOM/fetch shell + click-through"
Finding: The original task-map wording ("wires clickable-tile clicks to `IncidentApp`'s
filter-and-reload entry point") named a hook that doesn't exist — `static/js/incident.js` exports
no such function; filtering lives inside a closure-scoped `onFilterSubmit` handler.
Resolution: Reworded the task-map row to describe the actual non-invasive mechanism — populate
`#incident-filter-form`'s fields and call `requestSubmit()`, then dispatch a `click` on
`#nav-incidents` — which also better satisfies this spec's own Postcondition (dashboard-origin
filtering must behave identically to manual filtering). No spec-behavior change, task-map wording
only.

No security issues, no consistency contradictions against the charter, constitution, or sibling
specs.

## Verdict

**PASS_WITH_NOTES** — one warning, resolved via a task-map wording fix (no behavioral change to
the spec itself). Ready to plan.
