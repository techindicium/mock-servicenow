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
