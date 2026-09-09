---
charter: itsm-api
kind: behavioral
status: review-passed
risk_level: low
revision: 1
charter-revision: 1
amends: .context-index/specs/features/itsm-api/escalations.spec.md
target-revision: 2
created: 2026-09-09
updated: 2026-09-09
---

# Amendment: Live Spec: Escalation list, get, and update (targeting rev 2)

> This spec **amends** `.context-index/specs/features/itsm-api/escalations.spec.md` targeting revision 2.
> The base spec is immutable; this artifact carries the delta and is
> reviewed, planned, and validated on its own lifecycle.

## Amendment Rationale

The base spec's Preconditions state "Escalation create is out of scope this milestone" and that
the five seeded Escalations are the only rows `GET`/`PATCH` operate against "until a later
milestone adds `POST /escalations`." The itsm-api charter (revision 19) has now promoted
"Escalation create via API" from Deferred Capabilities to an active Capability Map row
(`Create Escalation`, must-have, milestone v2). This amendment supersedes that precondition and
adds the `POST /escalations` contract, unblocking the agent-ui charter's dependent (still
deferred) "Escalation create" UI capability.

## Behavioral Delta

### Superseded Precondition

The base spec's precondition "Escalation create is out of scope this milestone... until a later
milestone adds `POST /escalations`" no longer holds. `POST /escalations` exists as of this
amendment. The remaining base precondition (nullable `incident_number`/`owner` are ordinary,
non-exceptional values) is unchanged and applies equally to created Escalations.

### New Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-9** — **When** a `POST /escalations` request is sent with the required fields
  (`account_id`, `summary`) and no optional fields, **then** the API responds `201` with a new
  Escalation: `number` server-assigned as `ESCALATION-NNNN` (next-max-suffix scheme, mirroring
  `next_incident_number` — derived from the current max seeded/created suffix, never a separate
  counter, never colliding), `opened_at` server-assigned as the current UTC time in ISO format,
  `incident_number: null`, `owner: null`, `closed_at: null`.
- **BEH-10** — **When** a `POST /escalations` request additionally supplies `incident_number`
  and/or `owner`, **then** the API stores and returns those values exactly as given, alongside
  the server-assigned `number` and `opened_at`. `incident_number` is accepted as given without
  checking it against an existing Incident's `number` — this API enforces no foreign-key
  integrity on create, consistent with how `Incident.assigned_to`/`assignment_group` are already
  unenforced free-text references elsewhere in this API (charter Relationships section).
- **BEH-11** — **When** a `POST /escalations` request includes a `closed_at` value in the body,
  **then** the API silently ignores it — `closed_at` is not a creatable field (mirroring how
  `number`/`account_id`/`opened_at` are silently ignored on `PATCH`) — and the created Escalation's
  `closed_at` is `null` regardless of what was sent.
- **BEH-12** — **When** a `POST /escalations` request omits `account_id` or `summary`, **then**
  the API responds `422` naming the missing field(s) and persists no row.
- **BEH-13** — **When** a `POST /escalations` request body is malformed JSON, **then** the API
  responds `400` and persists no row.

### Postconditions (additive)

- A newly created Escalation is immediately visible on a subsequent `GET /escalations` and
  `GET /escalations/{number}` (subject to any `open_only`/`account_id` filter) — no eventual
  consistency window, consistent with the base spec's `PATCH` postcondition.
- A created Escalation's `number` never changes once assigned, consistent with the base spec's
  "number and account_id never change once seeded or created" postcondition.

### Error Cases (additive)

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| `POST /escalations` missing `account_id` and/or `summary` | `422 Unprocessable Entity`, JSON body naming the missing field(s) | `VALIDATION_ERROR` |
| `POST /escalations` malformed JSON request body | `400 Bad Request` | `MALFORMED_JSON` |

## System Constitution Reference

- **Principle 7:** "Breaking API changes are coordinated, not silent." — Applies because this
  amendment adds a new endpoint on an existing resource collection; it changes no existing path
  or response shape, so it is additive, not breaking.
- **Principle 6:** "Seeded discrepancies are load-bearing, not bugs... the two ownerless
  escalations... must persist across reseeds." — Applies because BEH-9/BEH-10 keep `owner` and
  `incident_number` ordinary nullable values on create, not something the API defaults away or
  rejects, consistent with how the base spec treats them on read/update.
- **Principle 3:** "Identifiers reconcile with the shared canon." — Applies because the new
  `number` values follow the existing `ESCALATION-NNNN` scheme and must not collide with the
  seeded `ESCALATION-04xx` range. `account_id` is accepted as given and not validated against
  the canon account list at create time — mirroring `POST /incidents`' existing `IncidentCreate`
  behavior, which likewise accepts `account_id` unvalidated. This is the established precedent in
  this API, not a new gap this amendment introduces.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Add `next_escalation_number` | Next-max-suffix `ESCALATION-NNNN` allocator in `app/db.py`, mirroring `next_incident_number` | small |
| Add `EscalationCreate` model | Pydantic model: `account_id`/`summary` required, `incident_number`/`owner` optional nullable, no `closed_at` field | small |
| Implement `POST /escalations` | Route handler: allocate number/opened_at, insert, return 201 with full representation | small |

## Acceptance Criteria

- [ ] `POST /escalations` with only required fields returns 201 with server-assigned `number`/`opened_at` and null `incident_number`/`owner`/`closed_at` (BEH-9)
- [ ] `POST /escalations` with `incident_number`/`owner` supplied stores and returns them exactly (BEH-10)
- [ ] `POST /escalations` silently ignores any `closed_at` in the request body (BEH-11)
- [ ] `POST /escalations` missing `account_id` or `summary` returns 422 naming the missing field(s) and persists nothing (BEH-12)
- [ ] `POST /escalations` with malformed JSON returns 400 and persists nothing (BEH-13)
- [ ] A created Escalation is immediately visible via `GET /escalations` and `GET /escalations/{number}`
- [ ] Created `number` values never collide with seeded `ESCALATION-04xx` rows
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
