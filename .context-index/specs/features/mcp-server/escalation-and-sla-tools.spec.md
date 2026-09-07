---
charter: mcp-server
status: review-passed
risk_level: low
milestone: mvp
revision: 1
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
---

# Live Spec: Escalation and SLA MCP tools (list_escalations, list_sla_records)

<!-- Live Spec within the mcp-server charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/mcp-server/charter.md -->

## Behavioral Contract

### Preconditions

- `itsm-api`'s `GET /escalations` and `GET /sla` endpoints are implemented and reachable at
  `API_BASE_URL`.
- Both tools in this spec are read-only; neither calls a mutating `itsm-api` endpoint. Per the
  mcp-server charter's Out of Scope, no `update_escalation` or single-fetch `get_escalation` tool
  exists in this milestone — a consumer needing either calls `itsm-api` directly.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** `list_escalations` is invoked with no arguments, **then** it calls
  `GET /escalations` with no query parameters and returns the full result unmodified, including
  any Escalation whose `owner` is `null`.
- **BEH-2** — **When** `list_escalations` is invoked with either or both of the optional
  `account_id`/`open_only` arguments, **then** it calls `GET /escalations` with the matching
  query parameters and returns the result unmodified.
- **BEH-3** — **When** `list_sla_records` is invoked with no arguments, **then** it calls
  `GET /sla` with no query parameters and returns the full result unmodified, including any
  `task_sla` record where `has_breached` is `true`.
- **BEH-4** — **When** `list_sla_records` is invoked with any combination of the optional
  `incident_number`/`breached`/`sla_definition` arguments, **then** it calls `GET /sla` with the
  matching query parameters and returns the result unmodified.
- **BEH-5** — **When** either tool in this spec is invoked with input that fails its declared
  input schema (e.g. a non-boolean `open_only` or `breached`), **then** the tool call errors
  before any HTTP request is made.
- **BEH-6** — **When** `itsm-api` is unreachable, or returns a `5xx` response, for either tool in
  this spec, **then** the tool call errors with a message naming the failure — connection failure
  or the API's `5xx` body passed through verbatim, whichever occurred.

### Postconditions

- Neither tool caches results; each call reflects `itsm-api`'s current state at call time.
- Neither tool filters, annotates, or otherwise adjusts the two seeded discrepancies these
  endpoints can surface (ownerless Escalations, breached `task_sla` records) — they pass through
  exactly as `itsm-api` returns them.

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Input fails the tool's input schema | Tool call errors immediately; no HTTP request made | `MCP_INPUT_INVALID` |
| API returns `422` (invalid filter value, e.g. an unknown `sla_definition`) | Tool call errors with the API's message verbatim | `MCP_UPSTREAM_ERROR` |
| API returns `5xx` | Tool call errors with the API's error body passed through verbatim | `MCP_UPSTREAM_ERROR` |
| API unreachable | Tool call errors with a clear connection message | `MCP_UPSTREAM_UNREACHABLE` |

## System Constitution Reference

- **Principle:** "The HTTP contract is the boundary." — Applies because these two tools are thin
  wrappers over `itsm-api`'s documented `/escalations` and `/sla` endpoints, never a direct
  database access.
- **Principle:** "Seeded discrepancies are load-bearing, not bugs." — Applies because these are
  the two tools most likely to surface the ownerless-Escalation and open-SLA-breach
  discrepancies to a calling agent; neither tool may filter, flag, or annotate them.
- **Principle:** "No inbound dependencies." — Applies because mcp-server depends on itsm-api,
  never the reverse.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Define tool schemas | JSON-schema input/output definitions for `list_escalations`/`list_sla_records`, registered with the MCP server | small |
| Wire HTTP calls | Translate each tool call into the matching `itsm-api` `/escalations` or `/sla` request | small |
| Error passthrough + connection handling | Verbatim upstream error passthrough (422/5xx) and a clear message on unreachable API | small |

## Acceptance Criteria

- [ ] `list_escalations` with no arguments returns the full unfiltered list, including ownerless Escalations (BEH-1)
- [ ] `list_escalations` with `account_id`/`open_only` returns the API's filtered result unmodified (BEH-2)
- [ ] `list_sla_records` with no arguments returns the full unfiltered list, including breached records (BEH-3)
- [ ] `list_sla_records` with `incident_number`/`breached`/`sla_definition` returns the API's filtered result unmodified (BEH-4)
- [ ] Schema-invalid input errors before any HTTP request, for both tools in this spec (BEH-5)
- [ ] An unreachable API or a `5xx` response produces a clear, verbatim-where-applicable error (BEH-6)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
