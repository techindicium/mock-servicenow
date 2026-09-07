---
last-reviewed-revision: 1
file-sha: "31d1a442ff30c33d8bcd77b6d3608dd2e2ba892fb29d4f14a41162840b7ababa"
rigor-tier: quick
---

# Architecture Review: incident-lifecycle

> **Date:** 2026-09-07
> **Spec:** .context-index/specs/features/itsm-api/incident-lifecycle.spec.md
> **Charter:** .context-index/specs/features/itsm-api/charter.md
> **Verdict:** PASS_WITH_NOTES

## Rigor Tier

Resolved: **quick** (source: risk policy — `risk_level: medium` frontmatter maps to
`policies.medium.review_mode: quick` in `.context-index/governance/risk-policies.yaml`).

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

- **SA-1** — *warning* — Location: Behaviors (BEH-5, POST /incidents). BEH-5 specifies defaults
  for `escalated`, `resolved_at`, and `assigned_to` when omitted on create, but says nothing about
  `opened_at` or `assignment_group`. BEH-8 later states `opened_at` is immutable via PATCH,
  implying it must be server-assigned at creation, but BEH-5 never confirms this or says whether a
  client-supplied `opened_at` is accepted, ignored, or rejected; no default is stated for
  `assignment_group` when omitted. Recommendation: add explicit creation behavior for `opened_at`
  (server-assigned, client value ignored/rejected) and a stated default for `assignment_group`.
- **SA-2** — *warning* — Location: Error Cases table; Behaviors (BEH-2). `GET /incidents` filters
  on `state`, `category`, and `escalated` (BEH-2), but no error case covers an invalid value for
  any of these (e.g. `escalated=notabool`, or a `state` value outside the fixed five), even though
  malformed `opened_after`/`opened_before` values are validated. Sibling specs (`sla-records`,
  `escalations`) explicitly validate their own filter enums. Recommendation: add error-case rows
  (or a BEH) for invalid `escalated`/`state`/`category` filter values.
- **SA-3** — *suggestion* — Location: Behaviors (BEH-1). The paginated list response's page
  metadata/query-param shape is never made concrete (shared gap across sibling list specs).
  Recommendation: define the pagination contract here or in a cross-cutting spec.

Not flagged (reviewed, no issue): the unguarded PATCH posture is correctly and explicitly
grounded in constitution Principle 5; the fixed five-value `state` enum and 1-4 `priority` range
are consistently validated; error-code vocabulary is consistent with sibling specs; no auth/
injection concerns introduced.

---

## Summary

**Total findings:** 3 (0 blockers, 2 warnings, 1 suggestion)
**Action required:** No blockers — ready for planning. Consider closing the `opened_at`/
`assignment_group` creation-default gap (SA-1) and the filter-validation gap (SA-2) during
implementation.

**Governance note:** `.context-index/governance/gates.yaml` `transitions` is empty — no
`spec-to-plan` `approver_role` is configured, so no human-approval footer applies here.
