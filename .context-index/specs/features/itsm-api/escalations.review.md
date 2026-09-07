---
last-reviewed-revision: 1
file-sha: "660e560c547582461919a1e7c4c162f395e172c23c8587ff95bca7460122f578"
rigor-tier: quick
---

# Architecture Review: escalations

> **Date:** 2026-09-07
> **Spec:** .context-index/specs/features/itsm-api/escalations.spec.md
> **Charter:** .context-index/specs/features/itsm-api/charter.md
> **Verdict:** PASS_WITH_NOTES

## Rigor Tier

Resolved: **quick** (source: risk policy — `risk_level: low` frontmatter maps to
`policies.low.review_mode: quick` in `.context-index/governance/risk-policies.yaml`).

## Reviewers Dispatched

| ID | Name | Mode | Profile | Prompt/Skill |
|----|------|------|---------|--------------|
| quick-synthesized-reviewer | Quick Synthesized Reviewer | subagent | reviewer-capable | plugin:review-specs/quick-synthesized-reviewer-prompt.md |

## Disabled Reviewers

| ID | Reason |
|----|--------|
| structural-architect | no reason given |
| security-reviewer | no reason given |
| consistency-analyzer | no reason given |

## Quick Synthesized Reviewer (quick-synthesized-reviewer)

**Verdict:** PASS_WITH_NOTES

- **SA-1** — *warning* — Location: Behaviors (BEH-6, PATCH mutable-field enumeration). BEH-6
  lists exactly `summary`, `owner`, `closed_at` as mutable and explicitly calls out `number`,
  `account_id`, `opened_at` as immutable/silently-ignored. `incident_number` — a nullable FK per
  the charter's Domain Model — is mentioned in neither list, leaving it unclear whether a PATCH
  body containing it is silently ignored or has undefined behavior. Recommendation: add
  `incident_number` to the immutable-fields callout in BEH-6.
- **SA-2** — *suggestion* — Location: Behaviors (BEH-6/BEH-7, closed_at reopening). BEH-7
  explicitly states an `owner: null` PATCH is valid and symmetric with the seeded ownerless
  state; no equivalent explicit statement exists for setting `closed_at` back to `null`
  (reopening a closed Escalation). Recommendation: add a short explicit behavior parallel to
  BEH-7 stating that PATCH may set `closed_at` to `null` to reopen an Escalation.
- **CON-1** — *suggestion* — Location: Error Cases table (filter-miss behavior). The sibling
  `sla-records.spec.md` explicitly documents that an unknown filter value on a list endpoint
  returns `200` with an empty array; this spec relies on BEH-2/BEH-3's wording to imply the same
  for `account_id`/`open_only` without stating it explicitly. Recommendation: add a table row (or
  short note) making this explicit, for consistency with `sla-records.spec.md`.

Not flagged (reviewed, no issue): treating `incident_number: null` and `owner: null` as normal,
valid states rather than errors is correctly and explicitly specified; error-code vocabulary is
consistent with sibling specs; no auth/injection concerns introduced.

---

## Summary

**Total findings:** 3 (0 blockers, 1 warning, 2 suggestions)
**Action required:** No blockers — ready for planning. Consider closing SA-1's
`incident_number`-mutability ambiguity during implementation.

**Governance note:** `.context-index/governance/gates.yaml` `transitions` is empty — no
`spec-to-plan` `approver_role` is configured, so no human-approval footer applies here.
