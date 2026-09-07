---
charter: mcp-server
status: implemented
risk_level: medium
milestone: mvp
revision: 2
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
source-manifest:
  sha: "0bbaa12"
  files:
    - mcp_server/client.py
    - mcp_server/config.py
    - mcp_server/errors.py
    - mcp_server/server.py
    - mcp_server/tools/incidents.py
    - requirements.txt
    - tests/mcp_server/conftest.py
    - tests/mcp_server/test_client.py
    - tests/mcp_server/test_incident_tools.py
  computed-at: "2026-09-07T19:11:43.949Z"
---

# Live Spec: Incident MCP tools (list/get/create/update)

<!-- Live Spec within the mcp-server charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/mcp-server/charter.md -->

## Behavioral Contract

### Preconditions

- `itsm-api`'s Incident endpoints (`GET /incidents`, `GET /incidents/{number}`,
  `POST /incidents`, `PATCH /incidents/{number}`) are implemented and reachable at
  `API_BASE_URL`.
- `number` is not a mutable field on `update_incident` and is silently ignored if present in its
  input — an Incident's identifier never changes after creation.
- No authentication is required to reach any `itsm-api` endpoint these tools wrap — per this
  repo's `platform-context.yaml` and the `itsm-api`/`mcp-server` charters' shared Quality
  Attributes ("No real auth. Bound to localhost only by default."), not a numbered constitution
  principle.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** `list_incidents` is invoked with any combination of the optional
  `account_id`, `state`, `category`, `opened_after`, `opened_before`, `escalated`, and pagination
  arguments, **then** it calls `GET /incidents` with the matching query parameters and returns
  the result unmodified.
- **BEH-2** — **When** `get_incident` is invoked with a `number` that exists, **then** it calls
  `GET /incidents/{number}` and returns the Incident.
- **BEH-3** — **When** `get_incident` is invoked with a `number` that does not exist, **then**
  the tool call errors with the API's `404` message passed through verbatim.
- **BEH-4** — **When** `create_incident` is invoked with all six fields the wrapped
  `POST /incidents` endpoint requires (`account_id`, `category`, `short_description`,
  `description`, `state`, `priority` — per `incident-lifecycle.spec.md` BEH-5, which defines no
  default for either `state` or `priority`), **then** it calls `POST /incidents` and returns the
  created Incident, including its server-assigned `number` and its server-assigned `opened_at`.
- **BEH-4b** — **When** `create_incident` is invoked with a field value `itsm-api` rejects on
  shape (e.g. a `category` outside the eight enumerated product areas, or a `priority` outside
  1–4), **then** the tool call errors with the API's `422` message passed through verbatim. The
  tool's own input schema validates only presence and type, not domain-value membership;
  value-level validation is delegated to `itsm-api`.
- **BEH-5** — **When** `update_incident` is invoked with one or more mutable fields (`state`,
  `priority`, `assigned_to`, `assignment_group`) against a `number` that exists, **then** it calls
  `PATCH /incidents/{number}` and returns the updated Incident. `number` is silently ignored if
  present in the input.
- **BEH-6** — **When** `update_incident` sets `state` to any value the API's state enum accepts
  (`new`, `in_progress`, `on_hold`, `resolved`, `closed`) — **including transitioning an Incident
  straight to `resolved` or `closed` while that Incident's `first_response` `task_sla` record
  shows `has_breached: true`, or while no customer-facing work note exists on it** — **then** the
  call succeeds unconditionally: `itsm-api` performs the transition, and `update_incident` returns
  the updated Incident with no refusal, no injected warning field, and no confirmation step. This
  holds regardless of the Incident's current state, its escalation flag, or the state of any of
  its `task_sla` records — `update_incident` carries no state-transition guard of any kind.
- **BEH-7** — **When** `update_incident` is invoked against a `number` that does not exist,
  **then** the tool call errors with the API's `404` message passed through verbatim.
- **BEH-8** — **When** `update_incident` is invoked with a field value `itsm-api` rejects on shape
  (e.g. a `state` outside the five enumerated values), **then** the tool call errors with the
  API's `422` message passed through verbatim.
- **BEH-9** — **When** any tool in this spec is invoked with input that fails its declared input
  schema (e.g. a missing required field, or a value of the wrong type), **then** the tool call
  errors before any HTTP request is made.
- **BEH-10** — **When** `itsm-api` is unreachable, or returns a `5xx` response, for any tool in
  this spec, **then** the tool call errors with a message naming the failure — connection failure
  or the API's `5xx` body passed through verbatim, whichever occurred — and never hangs, retries
  silently, or fabricates a response.

### Postconditions

- An Incident created or updated through these tools is immediately reflected in a subsequent
  `list_incidents`/`get_incident` call — no caching layer sits between this module and the API.
- `update_incident`'s success is never conditional on the resulting state being "safe" — BEH-6's
  unconditional-success guarantee is a permanent postcondition of this tool, not a one-time
  behavior.

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Input fails the tool's input schema | Tool call errors immediately; no HTTP request made | `MCP_INPUT_INVALID` |
| API returns `404` (unknown incident `number`) | Tool call errors with the API's message verbatim | `MCP_UPSTREAM_ERROR` |
| API returns `422` (invalid `category`/`priority`/`state` value that passed the tool's own schema but fails the API's) | Tool call errors with the API's message verbatim | `MCP_UPSTREAM_ERROR` |
| API returns `5xx` | Tool call errors with the API's error body passed through verbatim | `MCP_UPSTREAM_ERROR` |
| API unreachable | Tool call errors with a clear connection message | `MCP_UPSTREAM_UNREACHABLE` |

## System Constitution Reference

- **Principle:** "The HTTP contract is the boundary." — Applies because these four tools are thin
  wrappers over `itsm-api`'s documented Incident endpoints, never a direct database access.
- **Principle:** "The MCP tools stay unguarded." — Applies directly to BEH-6: `update_incident`
  must remain capable of any state transition, including resolving an Incident with an open SLA
  breach, and this spec forbids adding a permission check or state-transition guard here even
  though it would be easy to add one.
- **Principle:** "Seeded discrepancies are load-bearing, not bugs." — Applies because the
  "resolved with an open breach" seeded discrepancy depends on `update_incident` (and the seed
  loader) never refusing or correcting that state; this tool must not become the place that
  discrepancy gets fixed.
- **Principle:** "No inbound dependencies." — Applies because mcp-server depends on itsm-api,
  never the reverse.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Define tool schemas | JSON-schema input/output definitions for all four tools, registered with the MCP server | medium |
| Wire HTTP calls | Translate each tool call into the matching `itsm-api` Incident request | medium |
| Error passthrough + connection handling | Verbatim upstream error passthrough (404/422/5xx) and a clear message on unreachable API | small |
| Confirm no guard exists | Explicit test coverage proving `update_incident` succeeds when resolving an Incident with a breached `first_response` SLA — a regression here would silently violate Principle 5 | small |

## Acceptance Criteria

- [ ] `list_incidents` returns the API's filtered incident list unmodified (BEH-1)
- [ ] `get_incident` returns the Incident for a valid `number` (BEH-2)
- [ ] `get_incident` on an unknown `number` errors with the API's message verbatim (BEH-3)
- [ ] `create_incident` requires all six fields `POST /incidents` requires (including `state` and
      `priority`, neither defaulted) and creates and returns an Incident with its server-assigned
      `number` (BEH-4)
- [ ] `create_incident` with an invalid field value errors with the API's message verbatim (BEH-4b)
- [ ] `update_incident` updates the given mutable fields and returns the result; `number` is ignored (BEH-5)
- [ ] `update_incident` succeeds unconditionally when resolving/closing an Incident with an open SLA breach or no customer work note — no refusal, no injected warning, no confirmation step (BEH-6)
- [ ] `update_incident` on an unknown `number` errors with the API's message verbatim (BEH-7)
- [ ] `update_incident` with an invalid field value errors with the API's message verbatim (BEH-8)
- [ ] Schema-invalid input errors before any HTTP request, for every tool in this spec (BEH-9)
- [ ] An unreachable API or a `5xx` response produces a clear, verbatim-where-applicable error (BEH-10)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
