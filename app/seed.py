import csv
import hashlib
import json
from pathlib import Path

_FIXTURES = Path(__file__).parent / "fixtures" / "seed"

_RISKY_AREAS = {"billing", "integrations"}
_NARRATIVE_STATE_CYCLE = ["new", "in_progress", "on_hold"]

# The three narrative tickets whose subject/area mirror the pilot's two documented incidents
# (company.md's "pilot" section: INCIDENT-01 billing/superseded-refund-window,
# INCIDENT-02 integrations/webhook-retry) get a fixed, named work-note reply author instead of
# their own derived `assigned_to` — deterministic, not a random pick.
_NARRATIVE_FIXED_REPLY_AUTHOR = {
    "TICKET-004401": "Kofi Adjei",
    "TICKET-004417": "Kofi Adjei",
    "TICKET-004409": "Mei Tan",
}


class SeedError(RuntimeError):
    """Raised when the seed command cannot proceed. Carries a stable `code` for operators."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _stable_index(key: str, modulus: int) -> int:
    """A deterministic, cross-process-stable replacement for `hash(key) % modulus`. Python's
    builtin `hash()` is randomized per-process for strings (PYTHONHASHSEED) unless explicitly
    pinned, which would silently break BEH-2/BEH-4's "run after run" determinism the moment the
    seed command is invoked as two separate `python -m app.seed` processes rather than twice in
    the same test process. `hashlib` output does not vary by process, so it is used here instead
    of the plan prose's literal `hash(number)` while preserving the same intent: a pure,
    deterministic function of the incident's own `number`."""
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest, 16) % modulus


def _support_engineers(roster: dict) -> list:
    """The six Support Engineers with a non-null assignment_group (Tier 1 and Tier 2) — this
    excludes Mei Tan and Kofi Adjei, who carry role `Support Engineer` but a null
    `assignment_group` (see roster_seed.json's provenance note)."""
    return [
        u for u in roster["sys_users"]
        if u["role"] == "Support Engineer" and u["assignment_group"] is not None
    ]


def _derive_priority(tier: str, area: str) -> int:
    risky = area in _RISKY_AREAS
    if tier == "enterprise":
        return 1 if risky else 2
    if tier == "business":
        return 2 if risky else 3
    if tier == "standard":
        return 3 if risky else 4
    raise SeedError("SEED_DATA_INVALID", f"unknown account tier: {tier!r}")


def load_incidents_and_work_notes(conn) -> None:
    existing = conn.execute("SELECT COUNT(*) AS n FROM incidents").fetchone()["n"]
    if existing == 1307:
        return  # BEH-2: already seeded
    if existing not in (0, 1307):
        raise SeedError(
            "SEED_STATE_INCONSISTENT",
            f"incidents table has {existing} rows; expected 0 or 1307",
        )

    tiers_by_account = {
        a["account_id"]: a["tier"]
        for a in json.loads((_FIXTURES / "accounts_tiers.json").read_text())
    }
    roster = json.loads((_FIXTURES / "roster_seed.json").read_text())
    engineers = _support_engineers(roster)
    if len(engineers) != 6:
        raise SeedError(
            "SEED_DATA_INVALID",
            f"expected 6 Support Engineers with a non-null assignment_group, found {len(engineers)}",
        )

    with open(_FIXTURES / "tickets.csv", newline="") as f:
        historical_tickets = list(csv.DictReader(f))
    with open(_FIXTURES / "interactions.csv", newline="") as f:
        historical_interactions = list(csv.DictReader(f))
    narrative_tickets = json.loads((_FIXTURES / "narrative_tickets.json").read_text())

    interactions_by_ticket: dict = {}
    for row in historical_interactions:
        interactions_by_ticket.setdefault(row["ticket_id"], []).append(row)

    incident_rows = []
    work_note_rows = []

    def _derived_fields(number: str, account_id: str, area: str) -> dict:
        if account_id not in tiers_by_account:
            raise SeedError(
                "SEED_DATA_INVALID", f"unknown account_id {account_id!r} on incident {number!r}"
            )
        tier = tiers_by_account[account_id]
        priority = _derive_priority(tier, area)
        engineer = engineers[_stable_index(number, len(engineers))]
        return {
            "priority": priority,
            "assigned_to": engineer["name"],
            "assignment_group": engineer["assignment_group"],
        }

    # --- Historical tickets (all status: closed) ---
    for row in historical_tickets:
        number = row["ticket_id"]
        account_id = row["account_id"]
        area = row["area"]
        opened_at = row["opened_at"]
        if row["status"] != "closed":
            raise SeedError(
                "SEED_DATA_INVALID", f"unexpected status {row['status']!r} on ticket {number!r}"
            )
        derived = _derived_fields(number, account_id, area)
        notes = sorted(
            interactions_by_ticket.get(number, []), key=lambda r: r["occurred_at"]
        )
        for note in notes:
            actor = note["actor"]
            kind = note["kind"]
            if actor == "customer":
                created_by = "customer"
            elif actor == "assist":
                created_by = "assist"
            elif actor == "agent":
                created_by = derived["assigned_to"]
            else:
                raise SeedError(
                    "SEED_DATA_INVALID", f"unknown interaction actor {actor!r} on {number!r}"
                )
            if kind == "proposal_sent":
                note_type = "proposal_sent"
            elif kind == "message":
                note_type = "comment" if actor == "customer" else "work_note"
            else:
                raise SeedError(
                    "SEED_DATA_INVALID", f"unknown interaction kind {kind!r} on {number!r}"
                )
            work_note_rows.append(
                (note["interaction_id"], number, note["occurred_at"], created_by, note_type, note["body"])
            )
        resolved_at = notes[-1]["occurred_at"] if notes else None
        state = "closed"
        escalated = derived["priority"] == 1 and state != "closed"
        incident_rows.append(
            (
                number, account_id, area, row["subject"], row["body"], state,
                derived["priority"], opened_at, resolved_at,
                derived["assigned_to"], derived["assignment_group"], int(bool(escalated)),
            )
        )

    # --- Narrative tickets (ten, stay unresolved, live objects for Module 2 exercises) ---
    for index, ticket in enumerate(narrative_tickets):
        number = ticket["ticket_id"]
        account_id = ticket["account_id"]
        area = ticket["area"]
        opened_at = ticket["opened_at"]
        subject = ticket["subject"]
        body = ticket["body"]
        state = _NARRATIVE_STATE_CYCLE[index % len(_NARRATIVE_STATE_CYCLE)]
        derived = _derived_fields(number, account_id, area)

        reply_author = _NARRATIVE_FIXED_REPLY_AUTHOR.get(number, derived["assigned_to"])
        reply_time = _add_minutes(opened_at, 5)
        work_note_rows.append(
            (f"NARRATIVE-{number}-C", number, opened_at, "customer", "comment", body)
        )
        work_note_rows.append(
            (
                f"NARRATIVE-{number}-R", number, reply_time, reply_author, "work_note",
                f"Reviewed and responding to: {subject}",
            )
        )
        escalated = derived["priority"] == 1 and state != "closed"
        incident_rows.append(
            (
                number, account_id, area, subject, body, state,
                derived["priority"], opened_at, None,
                derived["assigned_to"], derived["assignment_group"], int(bool(escalated)),
            )
        )

    conn.execute("BEGIN")
    try:
        conn.executemany(
            """
            INSERT INTO incidents
                (number, account_id, category, short_description, description, state,
                 priority, opened_at, resolved_at, assigned_to, assignment_group, escalated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            incident_rows,
        )
        conn.executemany(
            """
            INSERT INTO work_notes
                (sys_id, incident_number, created_at, created_by, note_type, body)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            work_note_rows,
        )
    except Exception:
        conn.rollback()
        raise
    conn.commit()


def _add_minutes(iso_timestamp: str, minutes: int) -> str:
    from datetime import datetime, timedelta

    dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    dt += timedelta(minutes=minutes)
    return dt.isoformat().replace("+00:00", "Z")


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
