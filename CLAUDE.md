<!-- Synced from .context-index/constitution.md by adev. Do not edit above the User Additions line. -->

# Constitution: mock-servicenow

## Identity

mock-servicenow is a standalone mock of a ServiceNow-shaped ITSM API: incidents, work notes,
assignment groups, and SLA records. It is the system of record for Portwell's support desk in
the adev-course workspace, consumed by `portwell-engineering` (SDLC), `portwell-analytics` (DDLC), and
`portwell-knowledge` (KDLC).

It is course infrastructure, not a course exercise. Its own API surface and internals are not
something students build; they are a fixed dependency other tracks build against. Its MCP tools
are deliberately unguarded — `update_incident` and `add_work_note` carry no permission
boundaries — because Module 2's exercise is building a constrained wrapper over these tools, not
connecting to them. A guarded MCP would remove the exercise.

## Non-Negotiable Principles

1. **No inbound dependencies.** This repo never depends on `course-shared`, another `mock-*`
   repo, or any track repo. Consuming tracks depend on it; it never depends back.
2. **Fixture-backed, offline only.** No network call to a real endpoint, no real credentials.
   Everything this API serves comes from local fixtures.
3. **Identifiers reconcile with the shared canon.** `incident.number`, `account_id`, and user/
   group names must be consistent with `course-shared/canon/identifiers.md`, and the ten
   narrative tickets keep their exact identifiers because `portwell-engineering` tests key on them.
4. **The HTTP contract is the boundary.** Consuming tracks integrate through the documented API
   only, never by importing this repo's internals directly.
5. **The MCP tools stay unguarded.** `update_incident` and `add_work_note` must remain capable of
   any state transition or authorship, including resolving incidents with open SLA breaches and
   posting work notes as `assist`. Building safety around them is the exercise.
6. **Seeded discrepancies are load-bearing, not bugs.** The SLA business-hours/wall-clock
   disagreement, the two ownerless escalations, and incidents resolved with an open SLA breach
   must persist across reseeds and never be corrected or documented anywhere participants can
   read (record them only in `course-shared/heldout/seeded-defects.md`).
7. **Breaking API changes are coordinated, not silent.** Once a track depends on an endpoint or
   response shape, changing it requires updating this constitution's Context Routing table and
   flagging the affected tracks.

## Architecture Boundaries

### Requires Human Approval

- Breaking changes to the public HTTP API contract (endpoint paths, request/response shapes)
- Changing fixture data identifiers that other tracks may already key on
- Adding a dependency on another repo in the workspace
- Adding permission boundaries or guards to the MCP tools (contradicts Principle 5 by design)
- Correcting or documenting any of the three seeded discrepancies outside
  `course-shared/heldout/seeded-defects.md`

### Autonomous (Agent May Decide)

- Adding new mock endpoints that extend (not break) the existing contract
- Internal refactors that don't change the HTTP surface
- Adding tests
- Fixing lint errors

## Commands

```bash
pip install -r requirements.txt
python3 -m pytest -q    # tests
ruff check .             # lint
docker compose up        # run the full stack (itsm-api + mcp-server)
```

## Context Routing

| Context Need | Location |
|-------------|----------|
| API routes | *(not yet built — chartered via `/adev:brainstorm`)* |
| Fixture data | *(not yet built)* |
| Shared identifiers this mock must respect | `../course-shared/canon/identifiers.md` |
| Consumers of this API | `../adev-workspace.yaml` (`dependencies:` naming `mock-servicenow` as `to`) |
| Seeded discrepancies record | `../course-shared/heldout/seeded-defects.md` |

## Context Index

Structured project context lives under `.context-index/` — constitution, manifest, governance,
and scaffolding for specs, ADRs, and samples once this repo has code to describe.

## Governance Posture

Deliberately lightweight, for a small standalone mock API in a training course:

- **Reviewers** (`governance/review.yaml`): all three bundled reviewers disabled.
- **Validation** (`governance/validate.yaml`): only deterministic checks run; both
  subagent-review checks and visual-verification are disabled.
- **Risk policies** (`governance/risk-policies.yaml`): medium and low risk run `quick` mode,
  `minimal` test depth, no human-in-the-loop — most work here runs fully agentic. `high` risk
  keeps full rigor and human approval.
- `merge_policy: merge`, `protected_branches: []` — no remote/PR capability exists for this
  repo, so direct merges to `main` are allowed after gates pass. Always branch first regardless.

<!-- User Additions -->
