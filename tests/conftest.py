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
