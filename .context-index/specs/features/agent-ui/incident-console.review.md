---
spec: .context-index/specs/features/agent-ui/incident-console.spec.md
spec-revision: 3
date: 2026-09-09
tier: quick
verdict: PASS_WITH_NOTES
---

# Review: Incident console — revision 3 (Related Escalation panel, BEH-10)

Quick-tier synthesized review (structural + security + consistency, one pass). Scope limited to
BEH-10 and its new Preconditions bullet — BEH-1 through BEH-9, Postconditions, and Error Cases are
already-validated revision-2 content and were checked only for accidental drift (none found).

## Verification performed

- `app/models.py::EscalationRead` confirmed: `incident_number: str | None` is a real response
  field.
- `app/routers/escalations.py::GET /escalations` confirmed: only `account_id`/`open_only`/
  `page`/`page_size` params — no server-side `incident_number` filter, so client-side filtering is
  correct and the only option.
- BEH-1 through BEH-9, Postconditions, Error Cases confirmed textually unchanged from the
  validated revision-2 shape.
- No contradiction with constitution Principles 4 or 6.

## Findings

**SA-1** — severity: warning — location: BEH-10
Finding: Original wording assumed at most one Escalation could match an Incident's
`incident_number`, which neither this spec nor `escalations.spec.md` actually constrains.
Resolution: Added an explicit multi-match rule — first match by `number` ascending (the order
`GET /escalations` itself returns), with the expected case stated as 0-or-1.

**CON-1** — severity: suggestion — location: Preconditions (revision-3 bullet)
Finding: Original wording overstated `escalations-directory-nav.spec.md` BEH-2 as establishing
"the same pattern" including client-side filtering, when BEH-2 does no filtering at all (renders
every row unfiltered).
Resolution: Reworded to attribute only the fetch-full-unpaged-list half to BEH-2, and named the
filtering as new BEH-10 logic.

**CON-2** — severity: suggestion — location: BEH-10
Finding: Casing mismatch ("Unassigned" vs. BEH-2's "unassigned") given BEH-10 claims to match
BEH-2's convention.
Resolution: Aligned to lowercase "unassigned" and added a clarifying note that this is descriptive
prose, not a literal UI string either spec mandates.

**SEC-1** — severity: suggestion — location: Postconditions (textContent bullet)
Finding: No new safety gap (the existing general safe-rendering clause already covers Escalation
`summary`/`owner`), but the illustrative field list wasn't extended, reading as stale.
Resolution: Added "Escalation `summary`, `owner`" to the parenthetical.

**CON-3** — severity: suggestion — location: System Constitution Reference
Finding: The Principle 6 bullet cited only BEH-6; BEH-10 also surfaces a seeded discrepancy
(ownerless escalations) and wasn't mentioned.
Resolution: Extended the bullet to also cite BEH-10.

**SA-2** — severity: suggestion — location: frontmatter `milestone`
Finding: Spec-level `milestone: mvp` while the charter lists BEH-10's capability at `v1.2`.
Resolution: Not changed — the file legitimately spans milestones (BEH-1–9 are mvp, BEH-10 is a
v1.2 addition layered on the same validated file), consistent with how the charter already tracks
milestones per-capability rather than per-file. Noted, not actioned.

## Verdict

**PASS_WITH_NOTES** — one warning and four suggestions, all addressed via spec-text edits except
SA-2 (deliberately left as-is, reasoned above). No behavioral change beyond BEH-10 itself. Ready
to plan.
