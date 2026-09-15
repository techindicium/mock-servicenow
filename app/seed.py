import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
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
            elif actor == "portal":
                created_by = "portal"
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
    app startup (see this plan's Architecture section).

    Exit code distinguishes the two `SeedError` codes, so a caller (docker/itsm-api/entrypoint.sh)
    can react differently to each: `SEED_STATE_INCONSISTENT` (exit 2) only ever means a previous
    seed run was interrupted before finishing -- since every row this command writes comes from a
    committed fixture, that state is always safe to recover from by wiping the database and
    reseeding, never a reason to preserve anything. `SEED_DATA_INVALID` (exit 1) means the
    fixtures themselves disagree with this code's assumptions -- retrying against the same
    fixtures would just fail again the same way, so it is not treated as recoverable here."""
    import os
    import sys

    from app.db import create_schema, get_connection

    db_path = os.environ.get("DATABASE_PATH", "servicenow.db")
    conn = get_connection(db_path)
    try:
        create_schema(conn)
        seed_all(conn)
    except SeedError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        raise SystemExit(2 if exc.code == "SEED_STATE_INCONSISTENT" else 1) from exc


if __name__ == "__main__":
    main()
