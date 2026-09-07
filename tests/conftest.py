# Charter-wide foundation file (see plan header). Every sibling itsm-api plan's tests use the
# `client` fixture below unchanged, and use the `conn` fixture for direct fixture-row insertion
# (e.g. seeding a WorkNote, Escalation, TaskSla, SysUser, or AssignmentGroup row without an
# endpoint to create it through). Neither fixture is modified by any sibling plan.
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    application = create_app(str(tmp_path / "test.db"))
    return TestClient(application)


@pytest.fixture
def conn(client):
    return client.app.state.db_conn


def seed_task_sla(conn, **overrides):
    row = {
        "sys_id": "SLA-0001",
        "incident_number": "TICKET-000001",
        "sla_definition": "first_response",
        "target_minutes": 30,
        "actual_minutes": 20,
        "has_breached": 0,
        "business_time_only": 0,
    }
    row.update(overrides)
    conn.execute(
        """
        INSERT INTO task_sla
            (sys_id, incident_number, sla_definition, target_minutes, actual_minutes,
             has_breached, business_time_only)
        VALUES (:sys_id, :incident_number, :sla_definition, :target_minutes, :actual_minutes,
                :has_breached, :business_time_only)
        """,
        row,
    )
    conn.commit()
    return row


def seed_escalation(conn, **overrides):
    defaults = {
        "number": "ESCALATION-0001",
        "incident_number": None,
        "account_id": "ACC-1",
        "summary": "Test escalation",
        "opened_at": "2026-01-01T00:00:00Z",
        "closed_at": None,
        "owner": None,
    }
    defaults.update(overrides)
    conn.execute(
        "INSERT INTO escalations "
        "(number, incident_number, account_id, summary, opened_at, closed_at, owner) "
        "VALUES (:number, :incident_number, :account_id, :summary, :opened_at, :closed_at, :owner)",
        defaults,
    )
    conn.commit()
    return defaults
