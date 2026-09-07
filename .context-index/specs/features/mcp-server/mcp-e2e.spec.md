---
charter: mcp-server
status: validated
risk_level: medium
milestone: v1.1
revision: 2
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
source-manifest:
  sha: "5e33d80"
  files:
    - requirements-e2e.txt
    - tests/test_requirements_files.py
    - tests_e2e/breached_sla_fixture.py
    - tests_e2e/conftest.py
    - tests_e2e/mcp_client.py
    - tests_e2e/servers.py
    - tests_e2e/test_mcp_breached_sla_fixture.py
    - tests_e2e/test_mcp_client_helper.py
    - tests_e2e/test_mcp_error_paths_e2e.py
    - tests_e2e/test_mcp_escalation_sla_user_tools_e2e.py
    - tests_e2e/test_mcp_incident_tools_e2e.py
    - tests_e2e/test_mcp_server_fixture.py
    - tests_e2e/test_mcp_server_unreachable_fixture.py
    - tests_e2e/test_mcp_signature_round_trip_e2e.py
    - tests_e2e/test_mcp_tool_discovery_e2e.py
    - tests_e2e/test_mcp_work_note_tools_e2e.py
  computed-at: "2026-09-07T19:46:02.027Z"
---

# Live Spec: End-to-end MCP test suite (real client/transport)

<!-- Live Spec within the mcp-server charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/mcp-server/charter.md -->

## Behavioral Contract

### Preconditions

- All four other mcp-server specs (`incident-tools`, `work-note-tools`,
  `escalation-and-sla-tools`, `user-tools`) are implemented, including the streamable-http
  transport served at `/mcp`.
- These tests start two real processes: `itsm-api` (a live server process, seeded per its own
  seed command) and `mcp-server` itself, configured with `API_BASE_URL` pointed at `itsm-api`'s
  ephemeral port and its own `PORT` for the streamable-http transport.
- A real MCP client (e.g. the `mcp` SDK's `streamablehttp_client` + `ClientSession`) connects to
  the live `mcp-server` process over that real transport at `/mcp`. No test in this suite calls a
  tool function directly in-process — every call goes through the actual MCP protocol, the same
  way an external agent would use this server.
- The seeded fixture data includes at least one Incident whose `first_response` `task_sla`
  record has `has_breached: true` while the Incident itself is not yet `resolved`/`closed` — the
  scenario BEH-5 exercises. If the seed loader has not yet produced such a row when this suite
  runs, this suite's own setup creates one Incident and one matching breached `task_sla` record
  directly against `itsm-api`'s real HTTP surface (never by touching its database file) so BEH-5
  has a fixture to act on.

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** a real MCP client sends the protocol's tool-listing call to the live
  server, **then** it returns all 9 registered tools (`list_incidents`, `get_incident`,
  `create_incident`, `update_incident`, `list_work_notes`, `add_work_note`, `list_escalations`,
  `list_sla_records`, `list_users`) with their correct names and input schemas.
- **BEH-2** — **When** a real MCP client calls each of the four Incident tools against the live
  server, **then** the real CRUD operation happens — cross-verified by a direct real HTTP call to
  `itsm-api` after each mutating call.
- **BEH-3** — **When** a real MCP client calls `list_work_notes`/`add_work_note` against the live
  server, **then** the real read/write happens — cross-verified by a direct real HTTP call to
  `itsm-api`.
- **BEH-4** — **When** a real MCP client calls `list_escalations`, `list_sla_records`, and
  `list_users` against the live server, **then** the structured result each returns matches what
  a direct real HTTP call to `itsm-api` shows for the same data, including any ownerless
  Escalation or breached `task_sla` record present in the fixture.
- **BEH-5** — **This suite's signature scenario.** **When** a real MCP client, in one continuous
  session, (a) calls `create_incident` to create a new Incident, (b) calls `add_work_note` on
  that Incident with `created_by: "assist"`, and then (c) — with that Incident's
  `first_response` `task_sla` record showing `has_breached: true` (per the Preconditions'
  seeded-or-constructed fixture) and with no customer-facing work note ever added — calls
  `update_incident` to set `state: "resolved"` on it, **then** every one of the three calls
  succeeds over the real protocol with no error, no injected warning field in any response, and
  no confirmation step, and a direct real HTTP call to `itsm-api` afterward confirms the Incident
  is `resolved` while its `first_response` `task_sla` record still shows `has_breached: true`.
  This is the module's unguarded-by-design behavior from PRD.md, verified end to end rather than
  asserted only at the unit level.
- **BEH-6** — **When** a real MCP client calls a tool with input that fails its declared schema,
  **then** the client observes a `CallToolResult` with `isError: true` and the schema-violation
  message in `content` (never a raised transport-level/client-SDK exception — the session itself
  stays open) — the call never hangs and never reaches `itsm-api`.
- **BEH-7** — **When** `mcp-server` is started with `API_BASE_URL` pointed at a port nothing is
  listening on — a deliberately different topology from every other test in this suite, using its
  own dedicated fixture that starts `mcp-server` alone (no `itsm-api` process at all, rather than
  the shared dual-server fixture) — **then** a real MCP client's tool call still returns
  successfully at the MCP-session level, as a `CallToolResult` with `isError: true` naming the
  connection failure (the client-to-`mcp-server` transport itself is healthy; only the upstream
  hop fails) — not a hang, a crash, or a raised client-SDK exception.
- **BEH-8** — **When** `itsm-api` is running but returns a `5xx` for the specific request a tool
  call triggers, **then** the client observes a `CallToolResult` with `isError: true` carrying
  that `5xx` body through the protocol verbatim, not a generic or swallowed error.

### Postconditions

- Every assertion in this suite is made against what the real MCP client received over the real
  transport — never against `mcp_server`'s internal Python objects.
- BEH-5's Incident, once resolved with an open breach, is left in that state for the remainder of
  the test session — this suite never "cleans up" by correcting the seeded/constructed
  discrepancy it just demonstrated tolerating.
- Both server processes are torn down after the test session.

### Error Cases

The `E2E_*` codes below are this test suite's own internal assertion labels — names this suite's
test code uses to identify which case it is asserting — not codes expected to appear on the wire.
On the wire, each of these surfaces as a `CallToolResult(isError=True)` (see BEH-6/7/8) whose
`content` carries the underlying message (`MCP_INPUT_INVALID`/`MCP_UPSTREAM_ERROR`/
`MCP_UPSTREAM_UNREACHABLE` per the wrapped tool specs), except `E2E_SERVER_START_TIMEOUT`, which
is a test-setup failure with no protocol-level counterpart.

| Condition | Expected Behavior | Error Code (suite-internal label) |
|-----------|-------------------|------------|
| Real MCP client calls a tool with schema-invalid input | `CallToolResult(isError=True)` returned to the client; no upstream HTTP call made | `E2E_MCP_INPUT_INVALID` |
| `mcp-server` cannot reach `itsm-api` (BEH-7 setup) | `CallToolResult(isError=True)` naming the connection failure | `E2E_MCP_UPSTREAM_UNREACHABLE` |
| `itsm-api` returns a `5xx` for a tool-triggered request (BEH-8) | `CallToolResult(isError=True)` carrying the `5xx` body verbatim | `E2E_MCP_UPSTREAM_ERROR` |
| Either real server process fails to become healthy within the startup timeout | Test setup fails loudly, naming which process and the timeout | `E2E_SERVER_START_TIMEOUT` |

## System Constitution Reference

- **Principle:** "The HTTP contract is the boundary." — Applies because this suite verifies
  mcp-server's real, end-to-end path to that boundary — client → MCP protocol → mcp-server → real
  HTTP → itsm-api — rather than any single link in isolation.
- **Principle:** "The MCP tools stay unguarded." — Applies directly to BEH-5, this suite's
  signature scenario: the full create → work-note-as-assist → resolve-with-open-breach round trip
  must succeed end to end over the real protocol, with no guard anywhere in the path intercepting
  it.
- **Principle:** "Seeded discrepancies are load-bearing, not bugs." — Applies because BEH-5's
  postcondition explicitly leaves the demonstrated discrepancy uncorrected, and BEH-4 asserts
  ownerless Escalations and breached SLA records pass through unfiltered.
- **Principle:** "No inbound dependencies." — Applies because this suite still only drives
  mcp-server through its real client-facing surface; it never reaches into itsm-api's internals
  except via the same real HTTP calls the other specs already use.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Dual-server e2e fixture | A pytest fixture starting both `itsm-api` (real seeded process) and `mcp-server` as real processes, wired together via `API_BASE_URL`, torn down together | medium |
| mcp-server-only e2e fixture | A separate, narrower fixture for BEH-7 that starts only `mcp-server`, with `API_BASE_URL` pointed at a port nothing listens on | small |
| Real MCP client helper | A small helper wrapping the `mcp` SDK's `streamablehttp_client`/`ClientSession` connect-and-call pattern, reused across this suite's tests | medium |
| Tool-discovery e2e test | Real-client test for BEH-1 | small |
| Incident/work-note/escalation/SLA/user e2e tests | Real-client tests for BEH-2, BEH-3, BEH-4, cross-verified via real HTTP | medium |
| Breached-SLA fixture helper | Ensures at least one Incident + breached `first_response` `task_sla` record exists via real HTTP calls, for BEH-5 | small |
| Signature round-trip e2e test | Real-client test for BEH-5: create → add_work_note(assist) → update_incident(resolved) despite open breach, with post-hoc verification via real HTTP | medium |
| Error-path e2e tests | Real-client tests for BEH-6, BEH-7, BEH-8 | small |

## Acceptance Criteria

- [ ] A real MCP client discovers all 9 tools with correct schemas (BEH-1)
- [ ] All four Incident tools work end to end over the real protocol, cross-verified via real HTTP (BEH-2)
- [ ] Work-note tools work end to end over the real protocol, cross-verified via real HTTP (BEH-3)
- [ ] Escalation/SLA/user list tools match real API state, including seeded discrepancies passed through unfiltered (BEH-4)
- [ ] The full create → add_work_note(assist) → update_incident(resolved-with-open-breach) round trip succeeds end to end with no guard, no warning, no confirmation step (BEH-5)
- [ ] Schema-invalid tool input surfaces a protocol-level error, no upstream call made (BEH-6)
- [ ] An unreachable upstream API surfaces a protocol-level connection error (BEH-7)
- [ ] An upstream `5xx` surfaces through the protocol verbatim (BEH-8)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
