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

# Live Spec: User MCP tool (list_users)

<!-- Live Spec within the mcp-server charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/mcp-server/charter.md -->

## Behavioral Contract

### Preconditions

- `itsm-api`'s `GET /users` endpoint is implemented and reachable at `API_BASE_URL`.
- No authentication is required to reach it, matching this module's other read tools.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** `list_users` is invoked, **then** it calls `GET /users` and returns the
  result as the tool's structured output unmodified. `list_users` takes no filter or pagination
  parameters in this milestone, mirroring PRD.md's `/users` endpoint.
- **BEH-2** — **When** `list_users` is invoked with any input at all (it declares no input
  parameters), **then** the tool call errors before any HTTP request is made, since any argument
  fails its declared (empty) input schema.
- **BEH-3** — **When** `itsm-api` is unreachable, or returns a `5xx` response, **then**
  `list_users` errors with a message naming the failure — connection failure or the API's `5xx`
  body passed through verbatim, whichever occurred.

### Postconditions

- `list_users` reflects `itsm-api`'s current `sys_user` directory at call time; no caching layer
  sits between this module and the API.

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Input fails the tool's (empty) input schema | Tool call errors immediately; no HTTP request made | `MCP_INPUT_INVALID` |
| API returns `5xx` | Tool call errors with the API's error body passed through verbatim | `MCP_UPSTREAM_ERROR` |
| API unreachable | Tool call errors with a clear connection message | `MCP_UPSTREAM_UNREACHABLE` |

## System Constitution Reference

- **Principle:** "The HTTP contract is the boundary." — Applies because this tool is a thin
  wrapper over `itsm-api`'s documented `/users` endpoint, never a direct database access.
- **Principle:** "Identifiers reconcile with the shared canon." — Applies because the SysUser
  names this tool returns must match `course-shared/canon/company.md`, the same canon `itsm-api`
  seeds from; this tool introduces no identifiers of its own.
- **Principle:** "No inbound dependencies." — Applies because mcp-server depends on itsm-api,
  never the reverse.

## Design Note: no `get_user` or assignment-group tool

Per the mcp-server charter's Out of Scope and Deferred Capabilities, PRD.md's nine-tool list has
no single-fetch user tool and no `list_assignment_groups` tool. `list_users` is judged sufficient
for this milestone; a consumer needing `/assignment_groups` directly calls `itsm-api`.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Define tool schema | JSON-schema input/output definition for `list_users` (empty input schema), registered with the MCP server | small |
| Wire HTTP call | Translate the tool call into `GET /users` | small |
| Error passthrough + connection handling | Verbatim upstream error passthrough (5xx) and a clear message on unreachable API | small |

## Acceptance Criteria

- [ ] `list_users` returns the API's user list unmodified (BEH-1)
- [ ] `list_users` invoked with any input errors before any HTTP request (BEH-2)
- [ ] An unreachable API or a `5xx` response produces a clear, verbatim-where-applicable error (BEH-3)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
