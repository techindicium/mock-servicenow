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
