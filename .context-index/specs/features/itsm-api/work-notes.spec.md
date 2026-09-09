---
charter: itsm-api
status: validated
risk_level: medium
milestone: mvp
revision: 1
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
source-manifest:
  sha: "f158489"
  files:
    - app/db.py
    - app/main.py
    - app/models.py
    - app/routers/work_notes.py
    - tests/conftest.py
    - tests/test_db.py
    - tests/test_work_notes.py
  computed-at: "2026-09-09T11:24:00.329Z"
---

# Live Spec: Work notes list and add

<!-- Live Spec within the itsm-api charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/itsm-api/charter.md -->

## Behavioral Contract

### Preconditions

- The `incident-lifecycle` spec's Incident table and endpoints exist — a WorkNote cannot be
  listed or added without an Incident to attach to.
- `POST /incidents/{number}/work_notes` applies no permission check and no authorship/content
  guard — per constitution Non-Negotiable Principle 5, this HTTP layer never adds a write guard
  the MCP `add_work_note` tool intentionally omits. Any request may post as `customer`, any agent
  name, or `assist`, and may set `note_type` to any of the four fixed values regardless of
  whether the note's actual content matches that type (e.g. a `state_change`-typed note whose
  body is a plain comment). "Unguarded" means no authorship/business-rule check — it does not
  mean no structural validation: `note_type` still must be one of the fixed, valid values (see
  Behaviors and Error Cases).

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** a `GET /incidents/{number}/work_notes` request is sent for a `number` that
  exists, **then** the API responds `200` with every WorkNote attached to that Incident, ordered
  by `created_at` ascending (chronological ticket timeline), paginated.
- **BEH-2** — **When** a `GET /incidents/{number}/work_notes` request is sent for a `number` that
  does not exist, **then** the API responds `404` naming the missing number.
- **BEH-3** — **When** a `POST /incidents/{number}/work_notes` request is sent with a `number`
  that exists and required fields `created_by`, `note_type`, `body`, **then** the API creates the
  WorkNote with a server-assigned `sys_id` in the `INTERACTION-NNNNNNN` scheme, `incident_number`
  set from the path, and a server-assigned `created_at` timestamp, and responds `201` with the
  full representation.
- **BEH-4** — **When** a `POST /incidents/{number}/work_notes` request sets `created_by` to
  `customer`, any agent name, or `assist`, **then** the API accepts it without checking that the
  name is a known user or that the actor is authorized to post as that author.
- **BEH-5** — **When** a `POST /incidents/{number}/work_notes` request sets `note_type` to a
  value outside `comment`, `work_note`, `state_change`, `proposal_sent`, **then** the API responds
  `422` naming the invalid value and its allowed values, and creates no WorkNote.
- **BEH-6** — **When** a `POST /incidents/{number}/work_notes` request is sent for a `number`
  that does not exist, **then** the API responds `404` naming the missing number, and creates no
  WorkNote.
- **BEH-7** — **When** a `POST /incidents/{number}/work_notes` request is missing a required
  field (`created_by`, `note_type`, `body`), **then** the API responds `422` naming the missing
  field, and creates no WorkNote.

### Postconditions

- Every WorkNote created via `POST` is immediately retrievable via a subsequent
  `GET /incidents/{number}/work_notes` for the same number — no eventual consistency window.
- Posting a WorkNote, including one with `note_type: state_change`, never mutates the parent
  Incident's `state` or any other Incident field — an actual state change happens only via
  `PATCH /incidents/{number}` (see `incident-lifecycle` spec). The two operations are independent;
  nothing in this API keeps them in sync automatically.
- A WorkNote's `sys_id` and `incident_number` never change once assigned.

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Unknown incident `number` on list/add | `404 Not Found`, JSON body naming the missing number | `INCIDENT_NOT_FOUND` |
| Missing required field on add | `422 Unprocessable Entity`, JSON body naming the missing field | `VALIDATION_ERROR` |
| Invalid `note_type` value on add | `422 Unprocessable Entity`, JSON body naming the invalid value and its allowed values | `VALIDATION_ERROR` |
| Malformed JSON request body | `400 Bad Request` | `MALFORMED_JSON` |

## System Constitution Reference

- **Principle 5:** "The MCP tools stay unguarded... `add_work_note` can post as any author,
  including `assist`." — Applies directly: BEH-4 is the explicit statement that this HTTP layer,
  which the MCP `add_work_note` tool wraps, adds no authorship guard either.
- **Principle 4:** "The HTTP contract is the boundary." — Applies because this spec defines the
  work-note slice of that contract, the mechanism first-response time is computed from.
- **Principle 3:** "Identifiers reconcile with the shared canon." — Applies because `sys_id`
  values follow the `INTERACTION-NNNNNNN` scheme identifiers.md reserves for this entity.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Define the WorkNote table | SQLite table per PRD.md's `work_note` schema, with `incident_number` FK | small |
| Implement `GET /incidents/{number}/work_notes` | Query by incident_number ordered by created_at, paginated, 404 if incident missing | small |
| Implement `POST /incidents/{number}/work_notes` | Validation (note_type enum only, no authorship check), sys_id generation, insert | medium |

## Acceptance Criteria

- [ ] `GET /incidents/{number}/work_notes` returns notes in chronological order for an existing incident (BEH-1)
- [ ] `GET /incidents/{number}/work_notes` returns 404 for an unknown incident (BEH-2)
- [ ] `POST /incidents/{number}/work_notes` creates a note with a server-assigned sys_id and returns 201 (BEH-3)
- [ ] `POST /incidents/{number}/work_notes` accepts any created_by value with no authorship check (BEH-4)
- [ ] `POST /incidents/{number}/work_notes` rejects an invalid note_type with 422 (BEH-5)
- [ ] `POST /incidents/{number}/work_notes` returns 404 for an unknown incident and creates nothing (BEH-6)
- [ ] `POST /incidents/{number}/work_notes` with a missing required field returns 422 (BEH-7)
- [ ] Posting a work note never mutates the parent incident's state or other fields
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
