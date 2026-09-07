---
charter: mcp-server
status: review-passed
risk_level: medium
milestone: mvp
revision: 1
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
---

# Live Spec: Work Note MCP tools (list_work_notes, add_work_note)

<!-- Live Spec within the mcp-server charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/mcp-server/charter.md -->

## Behavioral Contract

### Preconditions

- `itsm-api`'s WorkNote endpoints (`GET /incidents/{number}/work_notes`,
  `POST /incidents/{number}/work_notes`) are implemented and reachable at `API_BASE_URL`.
- The `incident-tools` spec is implemented — an agent typically calls `create_incident` or
  `list_incidents` first to obtain an `incident_number` before calling either tool in this spec.
- `sys_id` and `incident_number` are not accepted as mutable input fields on `add_work_note`
  beyond identifying which Incident the note attaches to; a WorkNote's `sys_id` is always
  server-assigned.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** `list_work_notes` is invoked with an `incident_number` that exists,
  **then** it calls `GET /incidents/{number}/work_notes` and returns the result unmodified,
  including pagination parameters if supplied.
- **BEH-2** — **When** `list_work_notes` is invoked with an `incident_number` that does not
  exist, **then** the tool call errors with the API's `404` message passed through verbatim.
- **BEH-3** — **When** `add_work_note` is invoked with a valid `incident_number`, `note_type`,
  and `body`, **then** it calls `POST /incidents/{number}/work_notes` and returns the created
  WorkNote, including its server-assigned `sys_id` and `created_at`.
- **BEH-4** — **When** `add_work_note` is invoked with `created_by` set to `customer`, to any
  agent name, or to `assist`, **then** the call succeeds unconditionally for every one of those
  values: the tool performs no check of who or what is actually invoking it, and does not
  restrict `created_by` to any subset of these values. Posting a work note as `assist` needs no
  different treatment, confirmation, or additional field than posting one as `customer` or as a
  named agent.
- **BEH-5** — **When** `add_work_note` is invoked against an `incident_number` that does not
  exist, **then** the tool call errors with the API's `404` message passed through verbatim.
- **BEH-6** — **When** `add_work_note` is invoked with a `note_type` value `itsm-api` rejects on
  shape (outside `comment`, `work_note`, `state_change`, `proposal_sent`), **then** the tool call
  errors with the API's `422` message passed through verbatim. The tool's own input schema
  validates only presence and type of `created_by`/`note_type`/`body`, not `note_type` domain-
  value membership or `created_by` identity — both are delegated to `itsm-api` or left entirely
  unchecked, per BEH-4.
- **BEH-7** — **When** either tool in this spec is invoked with input that fails its declared
  input schema (e.g. a missing `body`, or a non-string `created_by`), **then** the tool call
  errors before any HTTP request is made.
- **BEH-8** — **When** `itsm-api` is unreachable, or returns a `5xx` response, for either tool in
  this spec, **then** the tool call errors with a message naming the failure — connection failure
  or the API's `5xx` body passed through verbatim, whichever occurred.

### Postconditions

- A WorkNote added through `add_work_note` is immediately visible to a subsequent
  `list_work_notes` call on the same `incident_number` — no caching layer sits between this
  module and the API.
- `add_work_note`'s acceptance of any `created_by` value is a permanent postcondition of this
  tool, not a one-time behavior — no later revision of this spec may narrow it without an
  explicit, human-approved amendment (see this repo's constitution, "Requires Human Approval").

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Input fails the tool's input schema | Tool call errors immediately; no HTTP request made | `MCP_INPUT_INVALID` |
| API returns `404` (unknown `incident_number`) | Tool call errors with the API's message verbatim | `MCP_UPSTREAM_ERROR` |
| API returns `422` (invalid `note_type` that passed the tool's own schema but fails the API's) | Tool call errors with the API's message verbatim | `MCP_UPSTREAM_ERROR` |
| API returns `5xx` | Tool call errors with the API's error body passed through verbatim | `MCP_UPSTREAM_ERROR` |
| API unreachable | Tool call errors with a clear connection message | `MCP_UPSTREAM_UNREACHABLE` |

## System Constitution Reference

- **Principle:** "The HTTP contract is the boundary." — Applies because these two tools are thin
  wrappers over `itsm-api`'s documented WorkNote endpoints, never a direct database access.
- **Principle:** "The MCP tools stay unguarded." — Applies directly to BEH-4: `add_work_note`
  must remain capable of posting as any author, including `assist`, and this spec forbids adding
  an author-identity check against who is actually calling the tool.
- **Principle:** "No inbound dependencies." — Applies because mcp-server depends on itsm-api,
  never the reverse.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Define tool schemas | JSON-schema input/output definitions for `list_work_notes`/`add_work_note`, registered with the MCP server | small |
| Wire HTTP calls | Translate each tool call into the matching `itsm-api` WorkNote request | small |
| Error passthrough + connection handling | Verbatim upstream error passthrough (404/422/5xx) and a clear message on unreachable API | small |
| Confirm no author guard exists | Explicit test coverage proving `add_work_note` succeeds with `created_by: "assist"` with no identity check — a regression here would silently violate Principle 5 | small |

## Acceptance Criteria

- [ ] `list_work_notes` returns the API's work-note list unmodified for a valid `incident_number` (BEH-1)
- [ ] `list_work_notes` on an unknown `incident_number` errors with the API's message verbatim (BEH-2)
- [ ] `add_work_note` creates and returns a WorkNote with its server-assigned `sys_id` (BEH-3)
- [ ] `add_work_note` succeeds unconditionally for `created_by` of `customer`, any agent name, or `assist`, with no identity check (BEH-4)
- [ ] `add_work_note` on an unknown `incident_number` errors with the API's message verbatim (BEH-5)
- [ ] `add_work_note` with an invalid `note_type` errors with the API's message verbatim (BEH-6)
- [ ] Schema-invalid input errors before any HTTP request, for both tools in this spec (BEH-7)
- [ ] An unreachable API or a `5xx` response produces a clear, verbatim-where-applicable error (BEH-8)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
