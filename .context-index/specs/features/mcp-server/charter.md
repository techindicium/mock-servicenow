---
status: approved
kind: feature
revision: 21
updated: 2026-09-07
---

# Feature Charter: mcp-server

<!-- Feature Charter for the mcp-server module.
     This defines WHAT the module does and its boundaries, not HOW it is built.
     Live Specs within this charter define specific behavioral contracts. -->

## Business Intent

mcp-server exposes `itsm-api`'s incident/work-note/escalation/SLA/user operations as MCP tools,
so an AI agent working in a consuming course track (`portwell-assist`/SDLC, `portwell-analytics`/
DDLC, `portwell-knowledge`/KDLC) can read and act on Portwell's support desk directly through the
Model Context Protocol, without hand-rolling HTTP calls. Like `itsm-api`'s other clients, it owns
no persisted data and never touches the database directly.

Per PRD.md, these tools are **deliberately unguarded**: `update_incident` can move any incident to
any state, including resolving one with an open SLA breach or an unanswered customer;
`add_work_note` can post as any author, including `assist`. That is the point — Module 2 asks
students to build a *constrained wrapper* with explicit permission boundaries and failure
behaviour around these tools. A guarded MCP here would remove the exercise.

## Scope and Boundaries

### In Scope

- Exactly the nine MCP tools PRD.md's "MCP tools" section names: `list_incidents`,
  `get_incident`, `create_incident`, `update_incident`, `list_work_notes`, `add_work_note`,
  `list_escalations`, `list_sla_records`, `list_users`.
- A running MCP server process that translates each tool call into an HTTP call against
  `itsm-api` and returns its result (or its error) back through the tool response, served over
  streamable-http at `/mcp`, mirroring `mock-jira`'s transport choice.
- Structured, JSON-schema tool input/output definitions so any MCP client can discover the tools
  and their parameters without out-of-band documentation.
- No permission boundary, no state-transition guard, no author check on `update_incident` or
  `add_work_note` — see Non-Negotiable Principle 5 in this repo's constitution.

### Out of Scope

- MCP resources or prompts — only tools are in scope.
- Authentication — mirrors `itsm-api`'s no-real-auth stance.
- Real-time subscriptions/streaming tool results.
- Any persistence of its own — every read and write is delegated to `itsm-api`.
- Any tool for `escalations` update, `escalations` single-fetch, or `assignment_groups` — PRD.md's
  nine-tool list omits these; `itsm-api`'s REST surface covers them for a client that needs
  direct HTTP.
- Adding a permission/approval layer around `update_incident` or `add_work_note` — that
  constrained wrapper is the exercise for a *consuming* track to build, not this module's job.

### Dependencies

| Dependency | Type | Description |
|-----------|------|-------------|
| itsm-api | internal module | Sole source of data and sole executor of every write. This module never opens the SQLite file directly. |

## Domain Model

<!-- Like mock-jira's mcp-server, this module owns no persisted entities. The one concept below is
     a view/schema-side wrapper concept, never persisted. -->

### Entities

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| McpTool | A single MCP tool definition wrapping one itsm-api endpoint | `name`, `description`, `input_schema` (JSON Schema), `maps_to_endpoint` |

### Relationships

- Each McpTool maps to exactly one itsm-api endpoint; no tool spans more than one endpoint call.

### Invariants

- Every McpTool's `input_schema` validates before the wrapped HTTP call is made — a request the
  schema rejects never reaches `itsm-api`.
- A tool call's error response always carries the underlying API's error message verbatim; the
  MCP layer never swallows, rewrites, or adds a permission-denial response of its own.
- No McpTool call is refused on the grounds of what state it would produce (e.g. resolving an
  incident with an open breach) — the wrapper is transparent, not a gate.

## Capability Map

| Capability | Description | Priority | Milestone | Status |
|-----------|-------------|----------|-------|--------|
| list_incidents tool | Wraps `GET /incidents`, all filter/pagination parameters | must-have | mvp | validated |
| get_incident tool | Wraps `GET /incidents/{number}` | must-have | mvp | validated |
| create_incident tool | Wraps `POST /incidents` | must-have | mvp | validated |
| update_incident tool | Wraps `PATCH /incidents/{number}`, unguarded | must-have | mvp | validated |
| list_work_notes tool | Wraps `GET /incidents/{number}/work_notes` | must-have | mvp | validated |
| add_work_note tool | Wraps `POST /incidents/{number}/work_notes`, unguarded author | must-have | mvp | validated |
| list_escalations tool | Wraps `GET /escalations`, filter parameters | must-have | mvp | validated |
| list_sla_records tool | Wraps `GET /sla`, filter parameters | must-have | mvp | validated |
| list_users tool | Wraps `GET /users` | must-have | mvp | validated |
| End-to-end MCP test suite | A real MCP client, over the real streamable-http transport, against a live server process | must-have | v1.1 | validated |

## Deferred Capabilities

| Capability | Reason | Target Milestone | Depends On |
|-----------|--------|-------------|------------|
| get_escalation / update_escalation tools | Not in PRD.md's nine-tool list; a consumer needing this can call `itsm-api` directly | v2 | — |
| list_assignment_groups tool | Not in PRD.md's nine-tool list | v2 | — |
| Permission-boundary wrapper | Explicitly the *consuming* track's exercise (Module 2), never this module's | — | — |

## Interface Contracts

### Exposed APIs

| Interface | Type | Description |
|-----------|------|-------------|
| `list_incidents` | MCP tool | List Incidents, filtered and paginated |
| `get_incident` | MCP tool | Fetch one Incident |
| `create_incident` | MCP tool | Create an Incident |
| `update_incident` | MCP tool | Update an Incident — unguarded |
| `list_work_notes` | MCP tool | List an Incident's work notes |
| `add_work_note` | MCP tool | Add a work note — unguarded |
| `list_escalations` | MCP tool | List Escalations, filtered |
| `list_sla_records` | MCP tool | List Task SLA records, filtered |
| `list_users` | MCP tool | List SysUsers |

### Consumed APIs

| Interface | Source Module | Description |
|-----------|-------------|-------------|
| `GET /incidents` | itsm-api | Backs `list_incidents` |
| `GET /incidents/{number}` | itsm-api | Backs `get_incident` |
| `POST /incidents` | itsm-api | Backs `create_incident` |
| `PATCH /incidents/{number}` | itsm-api | Backs `update_incident` |
| `GET /incidents/{number}/work_notes` | itsm-api | Backs `list_work_notes` |
| `POST /incidents/{number}/work_notes` | itsm-api | Backs `add_work_note` |
| `GET /escalations` | itsm-api | Backs `list_escalations` |
| `GET /sla` | itsm-api | Backs `list_sla_records` |
| `GET /users` | itsm-api | Backs `list_users` |

## Quality Attributes

| Attribute | Requirement |
|-----------|-------------|
| Performance | Tool-call round trip (MCP call → HTTP call → response) is not latency-sensitive at course scale. |
| Availability | Single local process; restarting it is an acceptable recovery path. |
| Security | No real auth. Bound to localhost only by default — never exposed to a real network. Deliberately no write-guard — see Business Intent. |
| Observability | Tool errors surface the underlying API error message unchanged; no structured logging required beyond what aids local debugging. |
