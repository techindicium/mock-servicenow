---
charter: itsm-api
status: implemented
risk_level: low
milestone: mvp
revision: 1
charter-revision: 1
created: 2026-09-07
updated: 2026-09-07
kind: behavioral
source-manifest:
  sha: "f4beef0"
  files:
    - app/main.py
    - app/models.py
    - app/routers/escalations.py
    - tests/conftest.py
    - tests/test_escalations.py
  computed-at: "2026-09-07T18:33:26.171Z"
---

# Live Spec: Escalation list, get, and update

<!-- Live Spec within the itsm-api charter.
     This defines a specific behavioral contract that drives implementation and testing.
     Parent Charter: .context-index/specs/features/itsm-api/charter.md -->

## Behavioral Contract

### Preconditions

- The API process is running and its SQLite database is available.
- Escalation create is out of scope this milestone (see charter's Deferred Capabilities) — the
  five seeded Escalations are the only rows this spec's `GET`/`PATCH` operate against until a
  later milestone adds `POST /escalations`.
- `Escalation.incident_number` and `Escalation.owner` are both nullable, and null is a valid,
  ordinary value for either field — not an error, not a placeholder for missing data, and not
  something any endpoint in this spec treats as exceptional. Two of the five seeded Escalations
  have `owner: null` by design (see constitution Non-Negotiable Principle 6).

### Behaviors

<!-- retired-behavior-ids: (none) -->

- **BEH-1** — **When** a `GET /escalations` request is sent with no query parameters, **then**
  the API responds `200` with a paginated page of all Escalations, including any with
  `incident_number: null` and/or `owner: null`.
- **BEH-2** — **When** a `GET /escalations?account_id=...` request is sent, **then** the API
  responds `200` with exactly the Escalations matching that `account_id`, still paginated.
- **BEH-3** — **When** a `GET /escalations?open_only=true` request is sent, **then** the API
  responds `200` with exactly the Escalations whose `closed_at` is null, omitting any Escalation
  that has been closed.
- **BEH-4** — **When** a `GET /escalations/{number}` request is sent for a `number` that exists,
  **then** the API responds `200` with that Escalation's full representation, including
  `incident_number` and `owner` exactly as stored — `null` values are serialized as JSON `null`,
  never omitted from the response body and never causing an error.
- **BEH-5** — **When** a `GET /escalations/{number}` request is sent for a `number` that does not
  exist, **then** the API responds `404` naming the missing number.
- **BEH-6** — **When** a `PATCH /escalations/{number}` request is sent with one or more of
  `summary`, `owner`, `closed_at` for a `number` that exists, **then** the API updates exactly
  those fields and responds `200` with the full updated representation. `number`, `account_id`,
  and `opened_at` are not mutable fields and are silently ignored if present in the request body.
- **BEH-7** — **When** a `PATCH /escalations/{number}` request explicitly sets `owner` to `null`,
  **then** the API accepts it and stores the Escalation as ownerless — unassigning an owner is a
  valid operation, not an error, symmetric with the seeded ownerless state.
- **BEH-8** — **When** a `PATCH /escalations/{number}` request is sent for a `number` that does
  not exist, **then** the API responds `404` naming the missing number, and persists no change.

### Postconditions

- Every update via `PATCH /escalations/{number}` is immediately visible on a subsequent
  `GET /escalations/{number}` and in `GET /escalations` (subject to any `open_only`/`account_id`
  filter) — no eventual consistency window.
- Setting `closed_at` to a non-null value removes that Escalation from subsequent
  `GET /escalations?open_only=true` results.
- An Escalation's `number` and `account_id` never change once seeded or created.

### Error Cases

| Condition | Expected Behavior | Error Code |
|-----------|-------------------|------------|
| Unknown `number` on get/patch | `404 Not Found`, JSON body naming the missing number | `ESCALATION_NOT_FOUND` |
| Invalid `open_only` value (not a parseable boolean) | `422 Unprocessable Entity`, JSON body naming the invalid parameter | `VALIDATION_ERROR` |
| Malformed JSON request body on patch | `400 Bad Request` | `MALFORMED_JSON` |

## System Constitution Reference

- **Principle 6:** "Seeded discrepancies are load-bearing, not bugs... the two ownerless
  escalations... must persist across reseeds and must never be corrected." — Applies directly:
  BEH-4 and BEH-7 are the explicit statements that a null `owner` is a normal, always-valid state
  this API represents faithfully, never silently defaults or rejects.
- **Principle 4:** "The HTTP contract is the boundary." — Applies because this spec defines the
  Escalation slice of that contract, the entity `portwell-knowledge`'s monthly review packs quote.
- **Principle 3:** "Identifiers reconcile with the shared canon." — Applies because `number`
  values follow the `ESCALATION-NNNN` scheme and `account_id` values must be valid canon accounts.

## Actionable Task Map

| Task | Description | Estimated Complexity |
|------|-------------|---------------------|
| Define the Escalation table | SQLite table per PRD.md's `escalation` schema, nullable `incident_number`/`owner` | small |
| Implement `GET /escalations` with filters and pagination | Query builder for `account_id`/`open_only`, page params | small |
| Implement `GET /escalations/{number}` | Query by number, 404 if missing, null fields serialized as JSON null | small |
| Implement `PATCH /escalations/{number}` | Partial update of `summary`/`owner`/`closed_at`, explicit-null support for `owner` | small |

## Acceptance Criteria

- [ ] `GET /escalations` returns a paginated, unfiltered page including ownerless/unlinked rows (BEH-1)
- [ ] `GET /escalations?account_id=...` filters correctly (BEH-2)
- [ ] `GET /escalations?open_only=true` excludes closed escalations (BEH-3)
- [ ] `GET /escalations/{number}` returns 200 with null fields serialized as JSON null (BEH-4)
- [ ] `GET /escalations/{number}` returns 404 for an unknown number (BEH-5)
- [ ] `PATCH /escalations/{number}` updates summary/owner/closed_at and returns 200 (BEH-6)
- [ ] `PATCH /escalations/{number}` accepts an explicit null owner as a valid unassignment (BEH-7)
- [ ] `PATCH /escalations/{number}` returns 404 for an unknown number (BEH-8)
- [ ] All quality gates pass (tests, lint)
- [ ] No constitutional violations introduced
