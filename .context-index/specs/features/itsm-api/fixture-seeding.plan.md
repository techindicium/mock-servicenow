<!-- partial_schema: plan@1 -->

# Implementation Plan: Fixture seed data

> **Methodology:** adev
> **Charter:** .context-index/specs/features/itsm-api/charter.md
> **Spec:** .context-index/specs/features/itsm-api/fixture-seeding.spec.md
> **Review:** review-passed (2026-09-07)
> **Platform:** FastAPI (per charter's chosen shape, matching `mock-jira`), Python 3.11, SQLite

**Goal:** A documented, explicitly-invoked seed command (`python -m app.seed`, never wired into
FastAPI startup) that loads all six tables — `incidents`, `work_notes`, `escalations`, `task_sla`,
`sys_user`, `assignment_group` — from fixture files vendored into this repo at authoring time,
producing exactly 1,307 Incidents, 2,614 WorkNotes, 5 Escalations (2 ownerless), one-or-two
TaskSla rows per Incident, 11 SysUsers (matching `user-directory.spec.md` BEH-1's "roughly a
dozen" — the nine-person support team plus two more named canon individuals who appear
elsewhere in this fixture set), and 3 AssignmentGroups. Re-running it against an already-seeded
database is a no-op; the
ten narrative tickets keep their exact `number` and CSV-sourced content forever; the three
seeded discrepancies (SLA business-hours/wall-clock disagreement, two ownerless escalations,
resolved/closed incidents with an open `first_response` breach) are present from the first run
and never corrected by any run.

**Architecture — authoring-time vendoring, never a runtime read:** Per this spec's own
Preconditions and constitution Non-Negotiable Principle 1 ("No inbound dependencies"), every
external source this plan touches is copied **by value** into this repo, once, during
implementation of this plan — not read live at seed-command runtime, ever. Concretely:

- `../portwell-assist/data/seed/history/tickets.csv` (1,297 rows, all `status: closed`) and
  `interactions.csv` (2,594 rows) are copied verbatim into `app/fixtures/seed/tickets.csv` and
  `app/fixtures/seed/interactions.csv`.
- `../portwell-assist/data/tickets.json` — the **ten narrative tickets**
  (`TICKET-004401/04405/04409/04411/04417/04420/04424/04429/04433/04438`, the tickets
  `portwell-assist`'s own test suite keys on — verified by reading
  `portwell-assist/service/tests/test_api_contract.py`) — is copied verbatim into
  `app/fixtures/seed/narrative_tickets.json`. **1,297 + 10 = 1,307**; this is exactly BEH-1's
  Incident count, not a coincidence — the narrative tickets are the extra ten.
- `../portwell-assist/data/accounts.json` (account→tier mapping) and
  `../portwell-assist/data/tier-commitments.json` (tier→SLA-minutes table) are copied verbatim
  into `app/fixtures/seed/accounts_tiers.json` and `app/fixtures/seed/tier_commitments.json` —
  `task_sla.target_minutes` is derived from these, per PRD.md's "Derived from tier commitments
  and work-note timestamps."
- `../portwell-knowledge`'s escalation data lives inside pack workbooks
  (`data/packs/2026-07/{ACCOUNT-1001,ACCOUNT-1003,ACCOUNT-1008}-2026-07.xlsx`, sheet
  `escalations`), not a standalone sheet file — confirmed by opening each workbook with
  `openpyxl`. The five rows found there (`ESCALATION-0412/0418/0409/0415/0421`, with `Summary`
  and `Age (days)` as of the 2026-07-31 period end) are extracted **by value** into
  `app/fixtures/seed/escalations_seed.json`, a hand-authored JSON with a source-provenance
  comment (workbook path, sheet name, extraction date) — the same "copy the fact, not the file"
  principle `mock-jira`'s exemplar plan applied to `company.md`'s prose Named People table.
- `../course-shared/canon/company.md`'s Named People table (Rui Bastos, Priya Nair, Joao Pinto —
  the three named support-team members — plus Mei Tan and Kofi Adjei, Assist engineering's Head
  of Engineering and Staff Engineer, who appear elsewhere in this fixture set as the work-note
  authors on the narrative tickets that mirror `INCIDENT-01`/`INCIDENT-02`, satisfying
  `user-directory.spec.md` BEH-1's "other named individuals... roughly a dozen rows total")
  plus six invented names for the remaining Support Engineers/Solution Consultant (per
  `user-directory.spec.md` rev 2's reconciliation note) are copied by value into
  `app/fixtures/seed/roster_seed.json` — 11 SysUser rows total.

The running seed command (`app/seed.py`, invoked as `python -m app.seed`) never opens
`../portwell-assist`, `../portwell-knowledge`, or `../course-shared/*` — it reads only
`app/fixtures/seed/*`, files that live inside this repository. This satisfies the spec's
Postcondition "No seed run ever reaches a file path outside this repository" and constitution
Principle 1.

**Why a standalone command, not startup wiring (departure from the `mock-jira` exemplar):** The
spec's Preconditions are explicit that seeding is "a documented, explicitly-invoked step... distinct
from any implicit seed-on-startup behavior." `mock-jira`'s `fixture-seeding.plan.md` wired
`seed_if_empty()` into `app/main.py`'s `on_startup()`; this plan deliberately does **not** —
`app/seed.py` exposes a `main()` entry point run via `python -m app.seed` (documented in
`README.md`/Dockerfile as a one-time build-time or manual step), and `app/main.py` is not
modified by this plan at all.

**A finding this plan surfaces rather than papers over:** computing `first_response`'s
`has_breached` honestly (`actual_minutes > target_minutes`, wall-clock, from each historical
ticket's `opened_at` to its first `agent`/`assist` interaction) against the real vendored
timestamps yields breaches on roughly 900 of the 1,297 historical tickets — not "a small
number." This is not a bug in the derivation; it is mathematically expected given the account
mix (three Enterprise accounts — 30-minute first-response commitment — account for ~70% of
historical tickets) and `company.md`'s own canon fact ("Median first response is 94 minutes
against a Business-tier commitment of 60"). Task 4 below computes `has_breached` **honestly and
uniformly** for every TaskSla record — no per-incident special-casing, no forcing a false
negative to make a count look smaller, which would itself be exactly the kind of "fixing" a
seeded discrepancy that constitution Principle 6 forbids. The discrepancy-presence test (Task 7)
therefore asserts **existence** (`>= 1` resolved-or-closed Incident with an open `first_response`
breach), matching how BEH-5 and PRD.md actually word it ("a small number," not a specific bound)
rather than asserting an upper bound the real data cannot honestly satisfy. This magnitude
finding is recorded verbatim in the `seeded-defects.md` write-up (Task 7) so the record is
truthful about scope, not just existence.

**Constitution Validation:** No task adds a workspace-repo runtime dependency, a new pip
dependency beyond `openpyxl`-free hand-authored JSON (no `openpyxl` needed at seed-command
runtime — only used once, by the plan author, to extract the escalation rows), an auth flow, or
a breaking change to any already-shipped contract (there is none yet — this repo has no code).
No task is `[REQUIRES HUMAN APPROVAL]`.

---

## File Structure

**Create:**
- `app/fixtures/seed/tickets.csv` — verbatim copy of `portwell-assist/data/seed/history/tickets.csv`
- `app/fixtures/seed/interactions.csv` — verbatim copy of `.../interactions.csv`
- `app/fixtures/seed/narrative_tickets.json` — verbatim copy of `portwell-assist/data/tickets.json`
- `app/fixtures/seed/accounts_tiers.json` — verbatim copy of `portwell-assist/data/accounts.json`
- `app/fixtures/seed/tier_commitments.json` — verbatim copy of `portwell-assist/data/tier-commitments.json`
- `app/fixtures/seed/escalations_seed.json` — hand-authored, 5 rows extracted by value from the
  `portwell-knowledge` pack workbooks' `escalations` sheets, with a provenance comment
- `app/fixtures/seed/roster_seed.json` — hand-authored, 11 SysUser rows + 3 AssignmentGroup names,
  reconciled from `company.md`'s Named People table plus six invented names
- `app/seed.py` — `SeedError`, per-source loaders, `derive_task_sla()`, `seed_all(conn)`, `main()`
- `tests/test_seed.py` — all behaviors below

**Reference (read, do not modify — assumed to exist from sibling plans per the Parallelization
note below):**
- `app/db.py` — `get_connection()`, `create_schema()`. Per the 2026-09-07 cross-plan consistency
  pass, `incident-lifecycle.plan.md`'s Task 1 is this charter's canonical foundation owner: its
  `create_schema()` defines **all six** charter tables up front (`incidents`, `work_notes`,
  `escalations`, `task_sla`, `sys_user`, `assignment_group`), so this plan's `conn` fixture has the
  full schema pre-applied as soon as that one task has landed — `work-notes.plan.md`,
  `escalations.plan.md`, `sla-records.plan.md`, and `user-directory.plan.md` no longer each define
  their own table (they extend `app/models.py`/their own routers only)
- `tests/conftest.py` — the `client`/`conn` fixtures (isolated temp-file `sqlite3.Connection` +
  `TestClient`, `row_factory = sqlite3.Row`, `create_schema()` pre-applied) every test in this plan
  uses; cross-plan output (`incident-lifecycle.plan.md`'s Task 1), not created by this plan
- `.context-index/specs/features/itsm-api/{incident-lifecycle,work-notes,escalations,sla-records,
  user-directory}.spec.md` — the six tables' exact schemas
- `.context-index/specs/features/itsm-api/charter.md` — Domain Model, Capability Map
- `CLAUDE.md` — constitution: Principle 1 (no inbound deps), Principle 3 (canon reconciliation),
  Principle 6 (seeded discrepancies load-bearing)
- `../portwell-assist/data/seed/history/{tickets.csv,interactions.csv}`,
  `../portwell-assist/data/{tickets.json,accounts.json,tier-commitments.json}`,
  `../portwell-assist/service/tests/test_api_contract.py` (confirms the ten narrative ticket IDs)
  — read once, at this plan's authoring time, to produce the vendored copies above; never read
  again at seed-command runtime
- `../portwell-knowledge/data/packs/2026-07/{ACCOUNT-1001,ACCOUNT-1003,ACCOUNT-1008}-2026-07.xlsx`
  (sheet `escalations`) — read once at authoring time via `openpyxl`, to produce
  `escalations_seed.json`; never read again at runtime
- `../course-shared/canon/company.md` (Named People table, tier commitments narrative,
  "The reporting deadline" section for the three Enterprise accounts) — read once at authoring
  time to produce `roster_seed.json`; never read again at runtime

---

## Context Packets

> No `source-manifest.files[]` exists yet for this module (first implementation, no code in this
> repo). Context packets fall back to charter + this spec + the five sibling specs (schemas) +
> constitution + `mock-jira`'s `fixture-seeding.plan.md` (vendoring-pattern reference), per the
> "no source-manifest" fallback.

### Task 1 Context (vendor fixtures)
- Spec: Preconditions (authoring-time vendoring, non-negotiable), Error Cases (`SEED_DATA_INVALID`)
- Source files listed under "Reference" above, full read
- Row-count facts to preserve: 1,297 historical tickets, 2,594 historical interactions, 10
  narrative tickets, 5 escalation rows across 3 Enterprise-account packs, 11 roster rows (9
  support team + Mei Tan + Kofi Adjei)

### Task 2 Context (incidents + work_notes loader)
- Spec: BEH-1 (exact counts), BEH-2 (idempotency), BEH-3 (narrative ticket permanence), Error
  Cases (`SEED_DATA_INVALID`, `SEED_STATE_INCONSISTENT`)
- `app/fixtures/seed/{tickets.csv,interactions.csv,narrative_tickets.json}` (from Task 1)
- `app/db.py` schema for `incidents`/`work_notes` (`incident-lifecycle.plan.md` Task 1's output —
  read, do not modify)

### Task 3 Context (escalations loader)
- Spec: BEH-1 (5 rows), BEH-5 (2 ownerless, never corrected)
- `app/fixtures/seed/escalations_seed.json` (from Task 1)
- `escalations.spec.md` schema (nullable `incident_number`, nullable `owner`)

### Task 4 Context (task_sla derivation)
- Spec: BEH-4 (deterministic derivation), BEH-5 (both remaining discrepancies), Domain Model
  invariant (`business_time_only: true` for every `resolution` record)
- `app/fixtures/seed/{tier_commitments.json,accounts_tiers.json}` (from Task 1)
- `sla-records.spec.md` schema and Preconditions (`business_time_only` semantics)
- The magnitude finding documented in this plan's Architecture section

### Task 5 Context (sys_user / assignment_group loader)
- Spec: BEH-1 (roster size), `user-directory.spec.md` BEH-1/BEH-2/BEH-3 and its rev-2
  reconciliation note (six invented names)
- `app/fixtures/seed/roster_seed.json` (from Task 1)

### Task 6 Context (idempotency test)
- Spec: BEH-2 in full ("any number of repeated runs, not just a second one")
- `app/seed.py`'s `seed_all()` (from Tasks 2-5, full read)

### Task 7 Context (discrepancy-presence test + `seeded-defects.md`)
- Spec: BEH-5, Postconditions, Acceptance Criteria's `seeded-defects.md` line
- `../course-shared/heldout/seeded-defects.md` (write target, seed-time-of-landing only, per
  charter Dependencies table)
- The magnitude finding in this plan's Architecture section (verbatim content for the write-up)

---

## Parallelization

**Cross-plan note (this grammar has no way to express a cross-plan `Depends On`):** per the
2026-09-07 cross-plan consistency pass, `incident-lifecycle.plan.md`'s Task 1 is this charter's
canonical foundation owner — its `create_schema()` defines **all six** charter tables up front
(`incidents`, `work_notes`, `escalations`, `task_sla`, `sys_user`, `assignment_group`), so every
table this plan writes rows into already exists as soon as that **one** task has landed; the
sibling `work-notes.plan.md`, `escalations.plan.md`, `sla-records.plan.md`, and
`user-directory.plan.md` no longer each define their own table (they now extend
`app/models.py`/their own routers only, not `create_schema()`). **This plan's entire task list
(Tasks 1-7) is therefore gated on `incident-lifecycle.plan.md`'s Task 1 alone, not on any of the
other four sibling plans' endpoint-behavior work** — those plans' own routers are irrelevant to
seeding, which writes rows directly via the shared `conn` fixture/connection, never through an
HTTP endpoint. `/adev:route` and whoever sequences `/adev:implement` runs across this charter's
plans should treat `incident-lifecycle.plan.md`'s Task 1 as the hard prerequisite of this entire
plan.

- Group A (sequential, within this plan): Task 1 → {Task 2, Task 3, Task 5 — independent of each
  other once Task 1 lands} → Task 4 (needs Task 2's Incidents and WorkNotes) → Task 6 → Task 7.
- Tasks 2, 3, and 5 do not depend on each other and could run concurrently once Task 1's vendored
  fixtures exist, but all three are gated by the cross-plan prerequisite above regardless.

---

## Task Summary

| # | Title | Complexity | Strategy | Depends On | Files |
|---|-------|-----------|----------|------------|-------|
| 1 | Vendor source fixtures into this repo | medium | unit | *(cross-plan)* incident-lifecycle Task 1 | 7 create, 0 modify |
| 2 | Idempotent incidents + work_notes loader | large | unit | Task 1 | 1 create/modify, 1 test |
| 3 | Escalation loader (5 rows, 2 ownerless) | small | unit | Task 1 | 1 modify, 1 test |
| 4 | TaskSla derivation (both discrepancies) | medium | unit | Task 2 | 1 modify, 1 test |
| 5 | SysUser/AssignmentGroup loader | small | unit | Task 1 | 1 modify, 1 test |
| 6 | Full idempotency test across all six tables | small | unit | Tasks 2-5 | 1 test |
| 7 | Discrepancy-presence test + `seeded-defects.md` write-up | small | unit | Tasks 3, 4 | 1 test, 1 manual doc write |

**Granularity:** `per-behavior` (source: manifest — `test_policy.granularity: per-behavior`).
`tests/test_seed.py` is created once (Task 1's fixture-shape assertions) and extended by every
subsequent task, one behavior group at a time.

---

## Task Structure

### Task 1: Vendor source fixtures into this repo [specialist: none]

**Charter capability:** Seed fixture data
**Files:**
- Create: `app/fixtures/seed/tickets.csv`, `interactions.csv`, `narrative_tickets.json`,
  `accounts_tiers.json`, `tier_commitments.json`, `escalations_seed.json`, `roster_seed.json`
- Create: `tests/test_seed.py`

**Tests:** `tests/test_seed.py` (create — fixture-shape assertions, Error Case `SEED_DATA_INVALID`)

- [ ] **Write failing test**

```python
# tests/test_seed.py
import csv
import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "app" / "fixtures" / "seed"

# `conn` (used throughout this file, from Task 2 onward) is a pytest fixture provided by
# `tests/conftest.py` — cross-plan output, whichever of this charter's sibling plans lands
# first: an isolated temp-file `sqlite3.Connection` with `row_factory = sqlite3.Row` and
# `create_schema()` already applied, fresh per test. This plan does not create conftest.py;
# it only depends on that fixture existing, per the Parallelization note below.


def test_vendored_tickets_csv_has_expected_row_count():
    with open(FIXTURES / "tickets.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1297
    assert all(r["status"] == "closed" for r in rows)


def test_vendored_interactions_csv_has_expected_row_count():
    with open(FIXTURES / "interactions.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2594


def test_vendored_narrative_tickets_are_the_ten_portwell_assist_keys_on():
    narrative = json.loads((FIXTURES / "narrative_tickets.json").read_text())
    ids = {t["ticket_id"] for t in narrative}
    assert ids == {
        "TICKET-004401", "TICKET-004405", "TICKET-004409", "TICKET-004411",
        "TICKET-004417", "TICKET-004420", "TICKET-004424", "TICKET-004429",
        "TICKET-004433", "TICKET-004438",
    }
    # 1,297 historical + 10 narrative = BEH-1's exact 1,307
    with open(FIXTURES / "tickets.csv", newline="") as f:
        historical_count = len(list(csv.DictReader(f)))
    assert historical_count + len(narrative) == 1307


def test_vendored_escalations_seed_has_five_rows_two_ownerless():
    escalations = json.loads((FIXTURES / "escalations_seed.json").read_text())["escalations"]
    assert len(escalations) == 5
    assert sum(1 for e in escalations if e["owner"] is None) == 2
    assert {e["number"] for e in escalations} == {
        "ESCALATION-0409", "ESCALATION-0412", "ESCALATION-0415",
        "ESCALATION-0418", "ESCALATION-0421",
    }


def test_vendored_roster_has_eleven_named_people_and_three_groups():
    roster = json.loads((FIXTURES / "roster_seed.json").read_text())
    assert len(roster["sys_users"]) == 11  # 9 support team + Mei Tan + Kofi Adjei
    assert set(roster["assignment_groups"]) == {
        "Support Tier 1", "Support Tier 2", "Solution Consultants",
    }
    canon_named = {"Rui Bastos", "Priya Nair", "Joao Pinto", "Mei Tan", "Kofi Adjei"}
    names = {u["name"] for u in roster["sys_users"]}
    assert canon_named.issubset(names)
    assert len(names) == 11  # no accidental duplicate/collision
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_seed.py`
Expected: FAIL — `app/fixtures/seed/` does not exist yet.

- [ ] **Implement**

Copy the two CSVs and `tickets.json` verbatim (no transformation):

```bash
mkdir -p app/fixtures/seed
cp ../portwell-assist/data/seed/history/tickets.csv app/fixtures/seed/tickets.csv
cp ../portwell-assist/data/seed/history/interactions.csv app/fixtures/seed/interactions.csv
cp ../portwell-assist/data/tickets.json app/fixtures/seed/narrative_tickets.json
cp ../portwell-assist/data/accounts.json app/fixtures/seed/accounts_tiers.json
cp ../portwell-assist/data/tier-commitments.json app/fixtures/seed/tier_commitments.json
```

Hand-author `app/fixtures/seed/escalations_seed.json` (extracted by value from the three
Enterprise-account July pack workbooks' `escalations` sheets — verified via `openpyxl`, period
end 2026-07-31; `opened_at` computed as `period_end - age_days` at authoring time, a fixed value
copied in, never recomputed at runtime):

```json
{
  "_provenance": "Extracted from portwell-knowledge/data/packs/2026-07/{ACCOUNT-1001,ACCOUNT-1003,ACCOUNT-1008}-2026-07.xlsx, sheet 'escalations', period end 2026-07-31. Read once at plan-authoring time; never read again at seed-command runtime.",
  "escalations": [
    {"number": "ESCALATION-0412", "account_id": "ACCOUNT-1001", "incident_number": null, "summary": "EDI feed rejecting with E-114, root cause not identified", "opened_at": "2026-07-12T00:00:00Z", "closed_at": null, "owner": "Noor Haddad"},
    {"number": "ESCALATION-0418", "account_id": "ACCOUNT-1001", "incident_number": null, "summary": "Billing correction turnaround disputed", "opened_at": "2026-07-25T00:00:00Z", "closed_at": null, "owner": "Priya Nair"},
    {"number": "ESCALATION-0409", "account_id": "ACCOUNT-1003", "incident_number": null, "summary": "Cold chain temperature export missing rows", "opened_at": "2026-07-04T00:00:00Z", "closed_at": null, "owner": "Priya Nair"},
    {"number": "ESCALATION-0415", "account_id": "ACCOUNT-1008", "incident_number": null, "summary": "Cycle count variance threshold behaviour", "opened_at": "2026-07-20T00:00:00Z", "closed_at": null, "owner": null},
    {"number": "ESCALATION-0421", "account_id": "ACCOUNT-1008", "incident_number": null, "summary": "Reporting figure differs from the portal", "opened_at": "2026-07-27T00:00:00Z", "closed_at": null, "owner": null}
  ]
}
```

Hand-author `app/fixtures/seed/roster_seed.json` (three canon-named support-team people from
`company.md`'s Named People table — Rui Bastos, Priya Nair, Joao Pinto — plus six invented names
per `user-directory.spec.md` rev 2's reconciliation note, plus two more canon-named individuals
from outside the support team, Mei Tan and Kofi Adjei, who this fixture set's narrative-ticket
work notes name as authors (Task 2) — satisfying `user-directory.spec.md` BEH-1's "other named
individuals from the canon that appear elsewhere in this fixture set... roughly a dozen rows
total". All checked against `identifiers.md`'s and `company.md`'s full name lists for
collisions — none found):

```json
{
  "_provenance": "Named individuals from course-shared/canon/company.md's Named People table: the three support-team members (Rui Bastos, Priya Nair, Joao Pinto), plus Mei Tan and Kofi Adjei (Assist engineering), who appear as work-note authors on the pilot-linked narrative tickets. The remaining six support-team rows are invented at seed-authoring time per user-directory.spec.md rev 2, checked against course-shared/canon/{company.md,identifiers.md} for name collisions. company.md itself is never edited.",
  "sys_users": [
    {"name": "Rui Bastos", "role": "Support Manager", "assignment_group": null},
    {"name": "Joao Pinto", "role": "Support Engineer", "assignment_group": "Support Tier 1"},
    {"name": "Miguel Costa", "role": "Support Engineer", "assignment_group": "Support Tier 1"},
    {"name": "Ines Carvalho", "role": "Support Engineer", "assignment_group": "Support Tier 1"},
    {"name": "Diego Fernandes", "role": "Support Engineer", "assignment_group": "Support Tier 2"},
    {"name": "Aline Souza", "role": "Support Engineer", "assignment_group": "Support Tier 2"},
    {"name": "Tariq Osei", "role": "Support Engineer", "assignment_group": "Support Tier 2"},
    {"name": "Priya Nair", "role": "Solution Consultant", "assignment_group": "Solution Consultants"},
    {"name": "Noor Haddad", "role": "Solution Consultant", "assignment_group": "Solution Consultants"},
    {"name": "Mei Tan", "role": "Support Engineer", "assignment_group": null},
    {"name": "Kofi Adjei", "role": "Support Engineer", "assignment_group": null}
  ],
  "assignment_groups": ["Support Tier 1", "Support Tier 2", "Solution Consultants"]
}
```

Mei Tan and Kofi Adjei carry `assignment_group: null` — like the Support Manager, they sit
outside the three support tiers (they are Assist engineering staff, not support desk staff);
`user-directory.spec.md` BEH-3 only requires a **non-null** group membership to name one of the
three groups, so a null membership here is valid per that same spec's Preconditions
(`assignment_group` nullable). Their `role` is stored as `"Support Engineer"` even though
`company.md` gives them engineering titles, because `user-directory.spec.md`'s own Preconditions
fix `SysUser.role` to exactly three values (`Support Manager`, `Support Engineer`, `Solution
Consultant`) — this is a deliberate, documented simplification of their canon role for this
fixture's schema, not a factual claim about their day job.

`SeedError` (used by every subsequent task):

```python
# app/seed.py (new file, first content)
class SeedError(RuntimeError):
    """Raised when the seed command cannot proceed. Carries a stable `code` for operators."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/test_seed.py`
Expected: PASS

- [ ] **Commit**

Branch: `feat/itsm-api/fixture-seeding`

```bash
git add app/fixtures/seed/ app/seed.py tests/test_seed.py
git commit -m "feat(itsm-api): vendor seed fixture sources into the repo"
```

---

### Task 2: Idempotent incidents + work_notes loader [specialist: none]

**Charter capability:** Seed fixture data
**Depends on:** Task 1 (this plan); *(cross-plan)* `incident-lifecycle.plan.md` Task 1 (the
`incidents`/`work_notes` tables already exist in `create_schema()` — see Parallelization)
**Files:** Modify `app/seed.py` (add `load_incidents_and_work_notes()`), extend `tests/test_seed.py`

**Tests:** BEH-1 (counts), BEH-2 (idempotency for these two tables), BEH-3 (narrative
permanence), `SEED_DATA_INVALID`

- [ ] **Write failing test**

```python
# tests/test_seed.py (append)
def test_fresh_seed_loads_exact_incident_and_work_note_counts(conn):
    from app.seed import load_incidents_and_work_notes

    load_incidents_and_work_notes(conn)
    assert conn.execute("SELECT COUNT(*) AS n FROM incidents").fetchone()["n"] == 1307
    assert conn.execute("SELECT COUNT(*) AS n FROM work_notes").fetchone()["n"] == 2614


def test_narrative_tickets_keep_exact_number_and_csv_sourced_content(conn):
    from app.seed import load_incidents_and_work_notes

    load_incidents_and_work_notes(conn)
    row = conn.execute(
        "SELECT * FROM incidents WHERE number = 'TICKET-004417'"
    ).fetchone()
    assert row is not None
    assert row["account_id"] == "ACCOUNT-1001"
    assert row["category"] == "billing"
    assert row["short_description"] == "Refund window for over-billing"
    assert "How long do we have to raise a correction" in row["description"]


def test_incident_and_work_note_loading_is_idempotent(conn):
    from app.seed import load_incidents_and_work_notes

    load_incidents_and_work_notes(conn)
    first_pass = conn.execute(
        "SELECT number FROM incidents ORDER BY number"
    ).fetchall()

    load_incidents_and_work_notes(conn)  # second run, same connection
    second_pass = conn.execute(
        "SELECT number FROM incidents ORDER BY number"
    ).fetchall()

    assert conn.execute("SELECT COUNT(*) AS n FROM incidents").fetchone()["n"] == 1307
    assert conn.execute("SELECT COUNT(*) AS n FROM work_notes").fetchone()["n"] == 2614
    assert [r["number"] for r in first_pass] == [r["number"] for r in second_pass]
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_seed.py -k incident_and_work_note`
Expected: FAIL — `ImportError: cannot import name 'load_incidents_and_work_notes'`.

- [ ] **Implement**

Design, in prose (full row-by-row code omitted — 1,307 rows is not something to hand-transcribe;
the algorithm below is what the implementer writes):

1. Read `narrative_tickets.json`; for each, `state` cycles deterministically through
   `["new", "in_progress", "on_hold"]` by list index (these ten stay **unresolved** — they are
   the live objects Module 2's `update_incident`/`add_work_note` exercises act on). Since no
   interaction source exists for them, synthesize exactly **two** WorkNotes per narrative ticket,
   deterministically from the ticket's own `subject`/`body`: a `customer` comment at `opened_at`
   quoting `body`, and one `work_note`-typed reply five minutes later. The reply's author is
   `assigned_to` (step 4 below) for seven of the ten; for the three narrative tickets whose
   `subject`/`area` mirror the pilot's two documented incidents (`TICKET-004401`/`TICKET-004417`,
   billing, mirroring `INCIDENT-01`'s superseded-refund-window story; `TICKET-004409`,
   integrations, mirroring `INCIDENT-02`'s webhook-retry story — both per
   `course-shared/canon/company.md`'s "pilot" section), the reply is authored by Kofi Adjei
   (Staff Engineer, Assist service) for the two integrations/billing-adjacent tickets and Mei Tan
   (Head of Engineering) for one — fixed, named, deterministic authorship, not a random pick, and
   the reason `roster_seed.json` carries these two names. Fixed content throughout, so BEH-3's
   "content byte-identical... across every run" holds trivially for these too. **10 × 2 = 20**;
   `2,594 + 20 = 2,614` — BEH-1's exact WorkNote count.
2. Read `tickets.csv`; every row's `status` is `closed` (verified in Task 1), map directly to
   `Incident.state = "closed"` (an honest, non-invented mapping of the one status the historical
   data actually records — see also Task 4's note on why the desk's real closed-ticket
   distribution is what produces the discrepancies, not synthetic random data).
3. `interactions.csv`'s `actor`/`kind` columns are generic (`customer`/`agent`/`assist`,
   `message`/`proposal_sent`) and do not carry a named agent or the four-value `note_type` enum
   directly — map deterministically, per row: `actor == "customer"` → `created_by = "customer"`;
   `actor == "assist"` → `created_by = "assist"`; `actor == "agent"` → `created_by` = that row's
   Incident's own derived `assigned_to` (step 4 below), so a ticket's notes are authored by
   whoever it is assigned to. `kind == "proposal_sent"` → `note_type = "proposal_sent"` directly;
   `kind == "message"` → `note_type = "comment"` when `actor == "customer"`, else `"work_note"`.
   This mapping is what Task 4's `derive_task_sla` relies on to find each Incident's first
   non-customer WorkNote.
4. For every Incident (historical and narrative), derive the fields the CSV source does not
   carry, **deterministically** (a pure function of `number`/`account_id`/`area`, no randomness,
   so BEH-2/BEH-4 hold across reruns):
   - `priority` (1-4): from account tier (via `accounts_tiers.json`) and whether `area` is one of
     `billing`/`integrations` (`company.md`: "the two consequential areas... high blast radius")
     — Enterprise+risky-area → 1, Enterprise+other or Business+risky-area → 2, Business+other or
     Standard+risky-area → 3, Standard+other → 4.
   - `assigned_to`/`assignment_group`: `hash(number) % 6` selects one of the six Support
     Engineers from `roster_seed.json` (three in `Support Tier 1`, three in `Support Tier 2`);
     `assignment_group` is that engineer's own group.
   - `escalated`: `true` when `priority == 1` and `state != "closed"`, else `false`.
   - `resolved_at`: for `state in ("resolved", "closed")`, the `occurred_at` of that Incident's
     chronologically last WorkNote; else `null`.
5. `load_incidents_and_work_notes(conn)`: if `SELECT COUNT(*) FROM incidents` already equals
   1307, return immediately (BEH-2 no-op). If it is `> 0` and `!= 1307`, raise
   `SeedError("SEED_STATE_INCONSISTENT", ...)` naming the actual count. Otherwise insert all
   1,307 Incidents and 2,614 WorkNotes inside a single transaction (`conn.execute("BEGIN")` /
   `conn.commit()`); any malformed row (unparseable `opened_at`, unknown `area`) raises
   `SeedError("SEED_DATA_INVALID", ...)` naming the offending row and file, and the transaction
   is rolled back so no partial insert survives.

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/test_seed.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/seed.py tests/test_seed.py
git commit -m "feat(itsm-api): load incidents and work notes from vendored fixtures, idempotently"
```

---

### Task 3: Escalation loader (5 rows, 2 ownerless) [specialist: none]

**Charter capability:** Seed fixture data
**Depends on:** Task 1 (this plan); *(cross-plan)* `incident-lifecycle.plan.md` Task 1 (the
`escalations` table already exists in `create_schema()`)
**Files:** Modify `app/seed.py` (add `load_escalations()`), extend `tests/test_seed.py`

**Tests:** BEH-1 (5 rows), BEH-5 (2 ownerless, present and never corrected)

- [ ] **Write failing test**

```python
# tests/test_seed.py (append)
def test_escalations_load_five_rows_two_ownerless(conn):
    from app.seed import load_escalations

    load_escalations(conn)
    rows = conn.execute("SELECT * FROM escalations").fetchall()
    assert len(rows) == 5
    assert sum(1 for r in rows if r["owner"] is None) == 2


def test_escalation_loading_is_idempotent(conn):
    from app.seed import load_escalations

    load_escalations(conn)
    load_escalations(conn)
    assert conn.execute("SELECT COUNT(*) AS n FROM escalations").fetchone()["n"] == 5
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_seed.py -k escalation`
Expected: FAIL — `ImportError: cannot import name 'load_escalations'`.

- [ ] **Implement**

```python
# app/seed.py (append)
import json
from pathlib import Path

_FIXTURES = Path(__file__).parent / "fixtures" / "seed"


def load_escalations(conn) -> None:
    existing = conn.execute("SELECT COUNT(*) AS n FROM escalations").fetchone()["n"]
    if existing == 5:
        return  # BEH-2: already seeded
    if existing not in (0, 5):
        raise SeedError(
            "SEED_STATE_INCONSISTENT",
            f"escalations table has {existing} rows; expected 0 or 5",
        )

    data = json.loads((_FIXTURES / "escalations_seed.json").read_text())
    for e in data["escalations"]:
        conn.execute(
            """
            INSERT INTO escalations
                (number, incident_number, account_id, summary, opened_at, closed_at, owner)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (e["number"], e["incident_number"], e["account_id"], e["summary"],
             e["opened_at"], e["closed_at"], e["owner"]),
        )
    conn.commit()
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/test_seed.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/seed.py tests/test_seed.py
git commit -m "feat(itsm-api): load the five seeded escalations, two ownerless by design"
```

---

### Task 4: TaskSla derivation (both remaining discrepancies) [specialist: none]

**Charter capability:** Seed fixture data
**Depends on:** Task 2 (needs Incidents + WorkNotes); *(cross-plan)* `incident-lifecycle.plan.md`
Task 1 (the `task_sla` table already exists in `create_schema()`)
**Files:** Modify `app/seed.py` (add `derive_task_sla()`), extend `tests/test_seed.py`

**Tests:** BEH-4 (determinism), BEH-5 (business-hours/wall-clock disagreement AND
resolved-with-open-breach, both present and never corrected)

- [ ] **Write failing test**

```python
# tests/test_seed.py (append)
def test_task_sla_derivation_is_deterministic_across_runs(conn):
    from app.seed import derive_task_sla, load_incidents_and_work_notes

    load_incidents_and_work_notes(conn)
    derive_task_sla(conn)
    first_pass = {
        r["sys_id"]: (r["target_minutes"], r["actual_minutes"], r["has_breached"])
        for r in conn.execute("SELECT * FROM task_sla").fetchall()
    }

    derive_task_sla(conn)  # re-run against the same data
    second_pass = {
        r["sys_id"]: (r["target_minutes"], r["actual_minutes"], r["has_breached"])
        for r in conn.execute("SELECT * FROM task_sla").fetchall()
    }
    assert first_pass == second_pass


def test_every_resolution_record_is_business_time_only(conn):
    from app.seed import derive_task_sla, load_incidents_and_work_notes

    load_incidents_and_work_notes(conn)
    derive_task_sla(conn)
    resolution_rows = conn.execute(
        "SELECT * FROM task_sla WHERE sla_definition = 'resolution'"
    ).fetchall()
    assert len(resolution_rows) > 0
    assert all(r["business_time_only"] for r in resolution_rows)
    first_response_rows = conn.execute(
        "SELECT * FROM task_sla WHERE sla_definition = 'first_response'"
    ).fetchall()
    assert all(not r["business_time_only"] for r in first_response_rows)


def test_resolved_or_closed_incident_with_open_first_response_breach_exists(conn):
    from app.seed import derive_task_sla, load_incidents_and_work_notes

    load_incidents_and_work_notes(conn)
    derive_task_sla(conn)
    rows = conn.execute(
        """
        SELECT i.number FROM incidents i
        JOIN task_sla t ON t.incident_number = i.number
        WHERE i.state IN ('resolved', 'closed')
          AND t.sla_definition = 'first_response'
          AND t.has_breached = 1
        """
    ).fetchall()
    assert len(rows) >= 1  # existence, not an upper bound — see plan Architecture section


def test_business_hours_resolution_disagrees_with_wall_clock_for_a_weekend_ticket(conn):
    from app.seed import (
        derive_task_sla,
        load_incidents_and_work_notes,
        _wall_clock_minutes_between,
    )

    load_incidents_and_work_notes(conn)
    derive_task_sla(conn)
    # At least one resolution record's business-hours actual_minutes differs from what a
    # wall-clock computation over the same [opened_at, resolved_at) interval would give —
    # this is discrepancy #1. 390 of the 1,297 historical tickets open on a weekend
    # (verified empirically against the vendored tickets.csv at plan-authoring time), so
    # material for this always exists.
    rows = conn.execute(
        """
        SELECT i.opened_at, i.resolved_at, t.actual_minutes FROM incidents i
        JOIN task_sla t ON t.incident_number = i.number
        WHERE t.sla_definition = 'resolution' AND i.resolved_at IS NOT NULL
        """
    ).fetchall()
    disagreements = 0
    for r in rows:
        wall_clock_minutes = _wall_clock_minutes_between(r["opened_at"], r["resolved_at"])
        if wall_clock_minutes != r["actual_minutes"]:
            disagreements += 1
    assert disagreements >= 1
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_seed.py -k task_sla or resolution or breach`
Expected: FAIL — `ImportError: cannot import name 'derive_task_sla'`.

- [ ] **Implement**

```python
# app/seed.py (append)
from datetime import datetime, timedelta, timezone

_BUSINESS_HOUR_START = 9
_BUSINESS_HOUR_END = 17  # 8-hour business day, Mon-Fri, matching company.md's support hours


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _wall_clock_minutes_between(start: str, end: str) -> int:
    return int((_parse_ts(end) - _parse_ts(start)).total_seconds() // 60)


def _business_minutes_between(start: str, end: str) -> int:
    """Elapsed minutes counting only Mon-Fri, 09:00-17:00 UTC: sum, day by day, the overlap of
    that day's business window with [start, end). Deterministic, pure function of its two
    timestamp arguments — the mechanism behind BEH-4's determinism requirement and the
    business-hours/wall-clock discrepancy (this value is never reconciled against
    `_wall_clock_minutes_between` anywhere in this codebase; a downstream consumer's own
    wall-clock computation over the same interval is expected to disagree for weekend-touching
    tickets — that disagreement is the seeded discrepancy, not a bug to fix here)."""
    start_dt, end_dt = _parse_ts(start), _parse_ts(end)
    if end_dt <= start_dt:
        return 0
    total_minutes = 0
    day = start_dt.date()
    while day <= end_dt.date():
        if day.weekday() < 5:  # Monday=0 .. Sunday=6
            day_start = datetime(day.year, day.month, day.day, _BUSINESS_HOUR_START, tzinfo=timezone.utc)
            day_end = datetime(day.year, day.month, day.day, _BUSINESS_HOUR_END, tzinfo=timezone.utc)
            overlap_start = max(start_dt, day_start)
            overlap_end = min(end_dt, day_end)
            if overlap_end > overlap_start:
                total_minutes += int((overlap_end - overlap_start).total_seconds() // 60)
        day += timedelta(days=1)
    return total_minutes


def _target_minutes(tier: str, sla_definition: str, tier_commitments: dict) -> int:
    commitment = tier_commitments[tier]
    if sla_definition == "first_response":
        return commitment["first_response_minutes"]
    if "resolution_business_hours" in commitment:
        return commitment["resolution_business_hours"] * 60
    return commitment["resolution_business_days"] * 8 * 60  # 8-hour business day


def derive_task_sla(conn) -> None:
    tier_commitments = json.loads((_FIXTURES / "tier_commitments.json").read_text())
    tiers_by_account = {
        a["account_id"]: a["tier"]
        for a in json.loads((_FIXTURES / "accounts_tiers.json").read_text())
    }

    incidents = conn.execute("SELECT * FROM incidents").fetchall()
    expected_max = len(incidents) * 2
    existing = conn.execute("SELECT COUNT(*) AS n FROM task_sla").fetchone()["n"]
    if existing > 0:
        return  # BEH-2: already derived once; never regenerate (BEH-4 stability)
    if existing > expected_max:
        raise SeedError(
            "SEED_STATE_INCONSISTENT",
            f"task_sla has {existing} rows, more than {expected_max} possible for {len(incidents)} incidents",
        )

    for incident in incidents:
        tier = tiers_by_account[incident["account_id"]]
        notes = conn.execute(
            "SELECT * FROM work_notes WHERE incident_number = ? ORDER BY created_at",
            (incident["number"],),
        ).fetchall()
        first_response_note = next(
            (n for n in notes if n["created_by"] != "customer"), None
        )

        # first_response: wall-clock, business_time_only = false
        fr_target = _target_minutes(tier, "first_response", tier_commitments)
        fr_actual = (
            _wall_clock_minutes_between(incident["opened_at"], first_response_note["created_at"])
            if first_response_note else None
        )
        fr_breached = fr_actual is not None and fr_actual > fr_target
        conn.execute(
            """INSERT INTO task_sla
               (sys_id, incident_number, sla_definition, target_minutes, actual_minutes,
                has_breached, business_time_only)
               VALUES (?, ?, 'first_response', ?, ?, ?, 0)""",
            (f"SLA-{incident['number']}-FR", incident["number"], fr_target, fr_actual, fr_breached),
        )

        # resolution: business-hours only, business_time_only = true (Domain Model invariant)
        if incident["state"] in ("resolved", "closed") and incident["resolved_at"]:
            res_target = _target_minutes(tier, "resolution", tier_commitments)
            res_actual = _business_minutes_between(incident["opened_at"], incident["resolved_at"])
            res_breached = res_actual > res_target
            conn.execute(
                """INSERT INTO task_sla
                   (sys_id, incident_number, sla_definition, target_minutes, actual_minutes,
                    has_breached, business_time_only)
                   VALUES (?, ?, 'resolution', ?, ?, ?, 1)""",
                (f"SLA-{incident['number']}-RES", incident["number"], res_target, res_actual, res_breached),
            )
    conn.commit()
```

`has_breached` is computed the same way, every time, for every Incident — no per-row
special-casing to force a particular discrepancy count. Discrepancy #1 (business-hours/wall-clock
disagreement) falls out of `_business_minutes_between` vs. `_wall_clock_minutes_between` disagreeing
whenever `[opened_at, resolved_at)` spans a weekend or off-hours segment. Discrepancy #3
(resolved/closed with an open `first_response` breach) falls out of the real historical
response-time distribution against the real Enterprise/Business/Standard commitments — honestly,
not manufactured (see this plan's Architecture section for the magnitude finding).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/test_seed.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/seed.py tests/test_seed.py
git commit -m "feat(itsm-api): derive TaskSla deterministically, preserving both SLA discrepancies"
```

---

### Task 5: SysUser / AssignmentGroup loader [specialist: none]

**Charter capability:** Seed fixture data
**Depends on:** Task 1 (this plan); *(cross-plan)* `incident-lifecycle.plan.md` Task 1 (the
`sys_user`/`assignment_group` tables already exist in `create_schema()`)
**Files:** Modify `app/seed.py` (add `load_roster()`), extend `tests/test_seed.py`

**Tests:** BEH-1 (11 SysUsers + 3 AssignmentGroups), `user-directory.spec.md` BEH-3 (every
SysUser's group names one of the three AssignmentGroups)

- [ ] **Write failing test**

```python
# tests/test_seed.py (append)
def test_roster_loads_eleven_sys_users_and_three_assignment_groups(conn):
    from app.seed import load_roster

    load_roster(conn)
    users = conn.execute("SELECT * FROM sys_user").fetchall()
    groups = conn.execute("SELECT * FROM assignment_group").fetchall()
    assert len(users) == 11
    assert {g["name"] for g in groups} == {
        "Support Tier 1", "Support Tier 2", "Solution Consultants",
    }
    group_names = {g["name"] for g in groups}
    for u in users:
        if u["assignment_group"] is not None:
            assert u["assignment_group"] in group_names


def test_roster_loading_is_idempotent(conn):
    from app.seed import load_roster

    load_roster(conn)
    load_roster(conn)
    assert conn.execute("SELECT COUNT(*) AS n FROM sys_user").fetchone()["n"] == 11
    assert conn.execute("SELECT COUNT(*) AS n FROM assignment_group").fetchone()["n"] == 3
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_seed.py -k roster`
Expected: FAIL — `ImportError: cannot import name 'load_roster'`.

- [ ] **Implement**

```python
# app/seed.py (append)
def load_roster(conn) -> None:
    existing = conn.execute("SELECT COUNT(*) AS n FROM sys_user").fetchone()["n"]
    if existing == 11:
        return  # BEH-2
    if existing not in (0, 11):
        raise SeedError(
            "SEED_STATE_INCONSISTENT", f"sys_user has {existing} rows; expected 0 or 11"
        )

    data = json.loads((_FIXTURES / "roster_seed.json").read_text())
    for group in data["assignment_groups"]:
        conn.execute("INSERT INTO assignment_group (name) VALUES (?)", (group,))
    for user in data["sys_users"]:
        conn.execute(
            "INSERT INTO sys_user (name, role, assignment_group) VALUES (?, ?, ?)",
            (user["name"], user["role"], user["assignment_group"]),
        )
    conn.commit()
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/test_seed.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/seed.py tests/test_seed.py
git commit -m "feat(itsm-api): load the eleven-person support directory and three assignment groups"
```

---

### Task 6: Full idempotency test across all six tables [specialist: none]

**Charter capability:** Seed fixture data
**Depends on:** Tasks 2-5
**Files:** Modify `app/seed.py` (add `seed_all()` orchestrator and `main()`), extend `tests/test_seed.py`

**Tests:** BEH-2 in full — "any number of repeated runs, not just a second one" — exercised
against the single orchestrated entry point every deployment actually calls.

- [ ] **Write failing test**

```python
# tests/test_seed.py (append)
def test_seed_all_is_idempotent_across_many_repeated_runs(conn):
    from app.seed import seed_all

    counts_after = []
    for _ in range(4):  # "any number of repeated runs, not just a second one" (BEH-2)
        seed_all(conn)
        counts_after.append({
            "incidents": conn.execute("SELECT COUNT(*) AS n FROM incidents").fetchone()["n"],
            "work_notes": conn.execute("SELECT COUNT(*) AS n FROM work_notes").fetchone()["n"],
            "escalations": conn.execute("SELECT COUNT(*) AS n FROM escalations").fetchone()["n"],
            "task_sla": conn.execute("SELECT COUNT(*) AS n FROM task_sla").fetchone()["n"],
            "sys_user": conn.execute("SELECT COUNT(*) AS n FROM sys_user").fetchone()["n"],
            "assignment_group": conn.execute("SELECT COUNT(*) AS n FROM assignment_group").fetchone()["n"],
        })
    fixed_counts = {k: v for k, v in counts_after[0].items() if k != "task_sla"}
    assert fixed_counts == {
        "incidents": 1307, "work_notes": 2614, "escalations": 5,
        "sys_user": 11, "assignment_group": 3,
    }
    assert counts_after[0]["task_sla"] > 0
    assert all(c == counts_after[0] for c in counts_after[1:])  # stable across all 4 runs


def test_seed_all_on_partial_database_raises_seed_state_inconsistent(conn):
    from app.seed import SeedError, load_incidents_and_work_notes, seed_all

    load_incidents_and_work_notes(conn)  # incidents seeded, everything else still empty
    with pytest.raises(SeedError) as exc_info:
        seed_all(conn)
    assert exc_info.value.code == "SEED_STATE_INCONSISTENT"
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_seed.py -k seed_all`
Expected: FAIL — `ImportError: cannot import name 'seed_all'`.

- [ ] **Implement**

```python
# app/seed.py (append)
_EXPECTED_COUNTS = {
    "incidents": 1307, "work_notes": 2614, "escalations": 5,
    "sys_user": 11, "assignment_group": 3,
}


def _table_counts(conn) -> dict:
    return {
        table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        for table in (*_EXPECTED_COUNTS, "task_sla")
    }


def seed_all(conn) -> None:
    """Idempotent, whole-database seed entry point. Empty database -> full seed. Already fully
    seeded (every fixed-count table matches, task_sla non-empty) -> no-op. Anything else (a
    partial prior run, a mid-migration state) -> SEED_STATE_INCONSISTENT, per this spec's Error
    Cases; this command never guesses."""
    counts = _table_counts(conn)
    if all(counts[t] == 0 for t in _EXPECTED_COUNTS) and counts["task_sla"] == 0:
        pass  # fresh database — fall through to full seed
    elif all(counts[t] == n for t, n in _EXPECTED_COUNTS.items()) and counts["task_sla"] > 0:
        return  # already fully seeded — BEH-2 no-op
    else:
        raise SeedError(
            "SEED_STATE_INCONSISTENT",
            f"seed state is neither empty nor fully seeded: {counts}",
        )

    load_incidents_and_work_notes(conn)
    load_escalations(conn)
    load_roster(conn)
    derive_task_sla(conn)  # last: reads the incidents/work_notes just loaded


def main() -> None:
    """`python -m app.seed` — the documented, explicitly-invoked seed command. Never called from
    app startup (see this plan's Architecture section)."""
    from app.db import create_schema, get_connection

    db_path = __import__("os").environ.get("ITSM_DB_PATH", "itsm.db")
    conn = get_connection(db_path)
    try:
        create_schema(conn)
        seed_all(conn)
    except SeedError as exc:
        import sys

        print(f"{exc.code}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
```

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/test_seed.py`
Expected: PASS

- [ ] **Commit**

```bash
git add app/seed.py tests/test_seed.py
git commit -m "feat(itsm-api): add seed_all() orchestrator and python -m app.seed entry point"
```

---

### Task 7: Discrepancy-presence test + `seeded-defects.md` write-up [specialist: none]

**Charter capability:** Seed fixture data
**Depends on:** Tasks 3, 4
**Files:** Extend `tests/test_seed.py`; one-time manual write to
`../course-shared/heldout/seeded-defects.md`

**Tests:** BEH-5 in full (all three discrepancies present and reproducible after every seed run)

- [ ] **Write failing test**

```python
# tests/test_seed.py (append)
def test_all_three_seeded_discrepancies_are_present_after_seeding(conn):
    from app.seed import seed_all

    seed_all(conn)

    # Discrepancy 1: at least one resolution record whose business-hours actual_minutes
    # disagrees with a wall-clock computation over the same interval.
    resolutions = conn.execute(
        """SELECT i.opened_at, i.resolved_at, t.actual_minutes FROM incidents i
           JOIN task_sla t ON t.incident_number = i.number
           WHERE t.sla_definition = 'resolution' AND i.resolved_at IS NOT NULL"""
    ).fetchall()
    from app.seed import _wall_clock_minutes_between
    assert any(
        _wall_clock_minutes_between(r["opened_at"], r["resolved_at"]) != r["actual_minutes"]
        for r in resolutions
    )

    # Discrepancy 2: exactly two ownerless escalations, out of exactly five.
    escalations = conn.execute("SELECT * FROM escalations").fetchall()
    assert len(escalations) == 5
    assert sum(1 for e in escalations if e["owner"] is None) == 2

    # Discrepancy 3: at least one resolved/closed incidents with an open first_response breach.
    breached = conn.execute(
        """SELECT COUNT(*) AS n FROM incidents i
           JOIN task_sla t ON t.incident_number = i.number
           WHERE i.state IN ('resolved', 'closed')
             AND t.sla_definition = 'first_response' AND t.has_breached = 1"""
    ).fetchone()["n"]
    assert breached >= 1


def test_reseeding_never_corrects_any_of_the_three_discrepancies(conn):
    from app.seed import seed_all

    seed_all(conn)
    before = conn.execute(
        "SELECT number, owner FROM escalations WHERE owner IS NULL ORDER BY number"
    ).fetchall()

    seed_all(conn)  # idempotent re-run
    after = conn.execute(
        "SELECT number, owner FROM escalations WHERE owner IS NULL ORDER BY number"
    ).fetchall()

    assert [r["number"] for r in before] == [r["number"] for r in after]
    assert len(after) == 2
```

- [ ] **Verify test fails**

Run: `python3 -m pytest -q tests/test_seed.py -k discrepan`
Expected: FAIL until Tasks 2-6 land in full (this task's tests are a superset assertion over the
whole pipeline, so they fail piecemeal until every earlier task's loader exists).

- [ ] **Verify test passes**

Run: `python3 -m pytest -q tests/test_seed.py`
Expected: PASS

- [ ] **Manual documentation action (not a runtime seed-command side effect)**

Per this spec's Preconditions ("Recording the three seeded discrepancies... is a one-time
documentation action performed by whoever implements this spec, coincident with landing the seed
command — not a write the running seed command performs at every invocation"), once the above
test passes, append the following to `../course-shared/heldout/seeded-defects.md` by hand (or via
a one-off script run once, never invoked by `app/seed.py` or any test):

```markdown
## mock-servicenow: itsm-api fixture seeding

Landed: <date this task lands>.

1. **SLA business-hours/wall-clock disagreement.** `task_sla.actual_minutes` for every
   `resolution`-definition record is computed in business hours only
   (`business_time_only: true`); an external wall-clock computation over the same
   `[opened_at, resolved_at)` interval disagrees whenever the interval spans a weekend. 390 of
   the 1,297 vendored historical tickets opened on a weekend.
2. **Two ownerless escalations.** Of the five seeded Escalations, `ESCALATION-0415` and
   `ESCALATION-0421` have `owner: null`, by design, and this never changes across reseeds.
3. **Resolved/closed incidents with an open `first_response` breach.** Computed honestly
   (`actual_minutes > target_minutes`, no per-row overrides), this is **not small** in the
   current fixture: roughly 900 of the 1,297 historical Incidents (all seeded `state: closed`)
   show `has_breached: true` on their `first_response` TaskSla record. This follows directly
   from the account mix (three Enterprise accounts — 30-minute first-response commitment — are
   ~70% of historical tickets) and the company's own documented median first-response time (94
   minutes, per `course-shared/canon/company.md`). Recorded here, not corrected, and not
   understated: PRD.md's "a small number" describes the narrative framing, not a count this
   implementation enforces.
```

This file is never read by any test or by `app/seed.py` — see constitution Principle 6 and
charter Dependencies ("not readable by participants during the course").

- [ ] **Commit**

```bash
git add tests/test_seed.py
git commit -m "test(itsm-api): assert all three seeded discrepancies survive every reseed"
# course-shared/heldout/seeded-defects.md is a separate repo; commit there per its own workflow.
```

---

## Quality Gates

After all tasks are complete, `/adev:validate` verifies the full quality gate suite. Results are
recorded in the validation report, not in this plan.

- **Test Suite** (`test`, deterministic, required, severity error): `python3 -m pytest -q`
- **Linter** (`lint`, deterministic, required, severity error): `ruff check .`
- All acceptance criteria from `fixture-seeding.spec.md` satisfied:
  - [ ] Fresh-database seed run loads all six tables with exact documented counts, no placeholder
    data (BEH-1) — Tasks 2, 3, 5
  - [ ] Re-running the seed command is idempotent, any number of times (BEH-2) — Task 6
  - [ ] The ten narrative tickets keep their exact identifiers/content across every reseed (BEH-3) — Task 2
  - [ ] TaskSla derivation is deterministic (BEH-4) — Task 4
  - [ ] All three seeded discrepancies are present and reproducible (BEH-5) — Task 7
  - [ ] No seed run reads or writes any path outside this repository at runtime — Architecture
    section (vendored fixtures only; `seeded-defects.md` write is a manual authoring-time action,
    not a runtime seed-command effect)
  - [ ] The three seeded discrepancies are recorded in `course-shared/heldout/seeded-defects.md`
    as a one-time delivery action — Task 7
- No constitutional violations: verified against Principles 1, 2, 3, 6 throughout this plan's
  Architecture section and each task's design.
