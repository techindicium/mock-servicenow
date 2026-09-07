from app.db import create_schema, get_connection, next_incident_number

_ALL_TABLES = (
    "incidents", "work_notes", "escalations", "task_sla", "sys_user", "assignment_group",
)


def test_create_schema_creates_incidents_table(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='incidents'"
    ).fetchone()
    assert row is not None


def test_create_schema_creates_all_six_charter_tables(tmp_path):
    # This is the charter-wide foundation (see plan header): every sibling itsm-api plan's
    # tests/conftest.py `conn`/`client` fixture depends on the full schema being present from
    # the first test onward, not just the incidents table this spec itself owns.
    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    existing = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    for table in _ALL_TABLES:
        assert table in existing


def test_next_incident_number_starts_at_ticket_000001(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    assert next_incident_number(conn) == "TICKET-000001"


def test_next_incident_number_never_collides_with_existing_rows(tmp_path):
    conn = get_connection(str(tmp_path / "test.db"))
    create_schema(conn)
    conn.execute(
        """
        INSERT INTO incidents
            (number, account_id, category, short_description, description, state,
             priority, opened_at, escalated)
        VALUES ('TICKET-000005', 'ACC-1', 'network', 'x', 'x', 'new', 1, '2026-01-01T00:00:00Z', 0)
        """
    )
    conn.commit()
    assert next_incident_number(conn) == "TICKET-000006"


# `work_notes` table creation is already covered by incident-lifecycle.plan.md's Task 1
# (cross-plan) test_create_schema_creates_all_six_charter_tables — no need to re-test it here.


def test_allocate_work_note_sys_id_starts_at_interaction_0000001(tmp_path):
    from app.db import allocate_work_note_sys_id

    db_path = tmp_path / "test.db"
    conn = get_connection(str(db_path))
    create_schema(conn)

    assert allocate_work_note_sys_id(conn) == "INTERACTION-0000001"


def test_allocate_work_note_sys_id_continues_after_existing_rows(tmp_path):
    from app.db import allocate_work_note_sys_id

    db_path = tmp_path / "test.db"
    conn = get_connection(str(db_path))
    create_schema(conn)
    # Simulate seeded rows using the same INTERACTION-NNNNNNN scheme, out of order,
    # to prove the allocator derives from MAX(existing), not COUNT(rows).
    conn.execute(
        "INSERT INTO work_notes (sys_id, incident_number, created_by, note_type, body) "
        "VALUES ('INTERACTION-0100000', 'TICKET-000001', 'assist', 'comment', 'seeded')"
    )
    conn.commit()

    assert allocate_work_note_sys_id(conn) == "INTERACTION-0100001"


def test_allocate_work_note_sys_id_never_collides_across_calls(tmp_path):
    from app.db import allocate_work_note_sys_id

    db_path = tmp_path / "test.db"
    conn = get_connection(str(db_path))
    create_schema(conn)

    seen = set()
    for _ in range(25):
        sys_id = allocate_work_note_sys_id(conn)
        assert sys_id not in seen
        seen.add(sys_id)
        conn.execute(
            "INSERT INTO work_notes (sys_id, incident_number, created_by, note_type, body) "
            "VALUES (?, 'TICKET-000001', 'assist', 'comment', 'x')",
            (sys_id,),
        )
        conn.commit()
