import re
import sqlite3

_NUMBER_RE = re.compile(r"^TICKET-(\d{6})$")


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Creates all six tables this charter's Domain Model defines. Only `incidents` is this
    spec's own responsibility; the other five (`work_notes`, `escalations`, `task_sla`,
    `sys_user`, `assignment_group`) are created here, up front, because every sibling
    itsm-api plan's tests/conftest.py `conn`/`client` fixture needs the full schema pre-applied
    from the first test onward — see plan header's Architecture note on this being the
    charter-wide canonical foundation. `CREATE TABLE IF NOT EXISTS` makes every statement
    additive and order-independent, so no sibling plan needs to touch this function's
    `incidents` statement, and this statement never needs to know about a sibling's rows."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS incidents (
            number TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            category TEXT NOT NULL,
            short_description TEXT NOT NULL,
            description TEXT NOT NULL,
            state TEXT NOT NULL,
            priority INTEGER NOT NULL,
            opened_at TEXT NOT NULL,
            resolved_at TEXT,
            assigned_to TEXT,
            assignment_group TEXT,
            escalated INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS work_notes (
            sys_id TEXT PRIMARY KEY,
            incident_number TEXT NOT NULL REFERENCES incidents(number),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            created_by TEXT NOT NULL,
            note_type TEXT NOT NULL,
            body TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS escalations (
            number TEXT PRIMARY KEY,
            incident_number TEXT,
            account_id TEXT NOT NULL,
            summary TEXT NOT NULL,
            opened_at TEXT NOT NULL,
            closed_at TEXT,
            owner TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS task_sla (
            sys_id TEXT PRIMARY KEY,
            incident_number TEXT NOT NULL,
            sla_definition TEXT NOT NULL,
            target_minutes INTEGER NOT NULL,
            actual_minutes INTEGER,
            has_breached INTEGER NOT NULL,
            business_time_only INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS assignment_group (
            name TEXT PRIMARY KEY
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sys_user (
            name TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            assignment_group TEXT REFERENCES assignment_group(name)
        )
        """
    )
    conn.commit()


def next_incident_number(conn: sqlite3.Connection) -> str:
    """Server-assigned, TICKET-NNNNNN, guaranteed not to collide with any existing row
    (seeded or previously created) — derived from the current max suffix, not a separate
    counter table, so it stays correct even once the fixture-seeding spec lands rows directly."""
    max_seq = 0
    for row in conn.execute("SELECT number FROM incidents"):
        match = _NUMBER_RE.match(row["number"])
        if match:
            max_seq = max(max_seq, int(match.group(1)))
    return f"TICKET-{max_seq + 1:06d}"
