def _create(conn, number, account_id="ACC-1", state="new", category="network", escalated=0,
            opened_at="2026-01-01T00:00:00Z"):
    conn.execute(
        """
        INSERT INTO incidents
            (number, account_id, category, short_description, description, state,
             priority, opened_at, escalated)
        VALUES (?, ?, ?, 'x', 'x', ?, 1, ?, ?)
        """,
        (number, account_id, category, state, opened_at, escalated),
    )
    conn.commit()


def test_list_incidents_unfiltered_returns_paginated_envelope(client):
    conn = client.app.state.db_conn
    for i in range(3):
        _create(conn, f"TICKET-00000{i}")
    resp = client.get("/incidents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["total"] == 3
    assert len(body["items"]) == 3


def test_list_incidents_filters_by_intersection_of_account_state_and_escalated(client):
    conn = client.app.state.db_conn
    _create(conn, "TICKET-000001", account_id="ACC-1", state="new", escalated=1)
    _create(conn, "TICKET-000002", account_id="ACC-1", state="resolved", escalated=1)
    _create(conn, "TICKET-000003", account_id="ACC-2", state="new", escalated=1)
    resp = client.get("/incidents?account_id=ACC-1&state=new&escalated=true")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["number"] == "TICKET-000001"


def test_list_incidents_opened_after_before_bound_inclusive_exclusive(client):
    conn = client.app.state.db_conn
    _create(conn, "TICKET-000001", opened_at="2026-01-01T00:00:00Z")
    _create(conn, "TICKET-000002", opened_at="2026-01-05T00:00:00Z")
    resp = client.get("/incidents?opened_after=2026-01-01T00:00:00Z&opened_before=2026-01-05T00:00:00Z")
    body = resp.json()
    assert [i["number"] for i in body["items"]] == ["TICKET-000001"]


def test_list_incidents_invalid_state_filter_returns_422(client):
    resp = client.get("/incidents?state=bogus")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "state" in body["message"]
    assert "new" in body["message"]


def test_list_incidents_invalid_escalated_filter_returns_422(client):
    resp = client.get("/incidents?escalated=maybe")
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_list_incidents_unrecognized_category_filter_returns_empty_not_error(client):
    conn = client.app.state.db_conn
    _create(conn, "TICKET-000001", category="network")
    resp = client.get("/incidents?category=nonexistent")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_list_incidents_invalid_opened_after_returns_422(client):
    resp = client.get("/incidents?opened_after=not-a-date")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "opened_after" in body["message"]


def test_get_incident_by_number_returns_200(client):
    conn = client.app.state.db_conn
    _create(conn, "TICKET-000042")
    resp = client.get("/incidents/TICKET-000042")
    assert resp.status_code == 200
    assert resp.json()["number"] == "TICKET-000042"


def test_get_incident_unknown_number_returns_404(client):
    resp = client.get("/incidents/TICKET-999999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "INCIDENT_NOT_FOUND"
    assert "TICKET-999999" in body["message"]
