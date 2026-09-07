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


_REQUIRED = {
    "account_id": "ACC-1", "category": "network", "short_description": "Router down",
    "description": "Router down since 9am", "state": "new", "priority": 2,
}


def test_create_incident_returns_201_with_server_assigned_number_and_defaults(client):
    resp = client.post("/incidents", json=_REQUIRED)
    assert resp.status_code == 201
    body = resp.json()
    assert body["number"] == "TICKET-000001"
    assert body["escalated"] is False
    assert body["resolved_at"] is None
    assert body["assigned_to"] is None
    assert body["assignment_group"] is None
    assert body["opened_at"] is not None


def test_create_second_incident_number_never_collides(client):
    client.post("/incidents", json=_REQUIRED)
    resp = client.post("/incidents", json=_REQUIRED)
    assert resp.json()["number"] == "TICKET-000002"


def test_create_incident_retrievable_immediately_via_get_list_and_get_by_number(client):
    created = client.post("/incidents", json=_REQUIRED).json()
    assert client.get(f"/incidents/{created['number']}").status_code == 200
    listed = client.get(f"/incidents?account_id={_REQUIRED['account_id']}").json()
    assert created["number"] in [i["number"] for i in listed["items"]]


def test_create_incident_missing_required_field_returns_422_and_creates_nothing(client):
    payload = dict(_REQUIRED)
    del payload["short_description"]
    resp = client.post("/incidents", json=payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "short_description" in body["message"]
    assert client.get("/incidents").json()["total"] == 0


def test_create_incident_invalid_state_returns_422_naming_allowed_values(client):
    payload = dict(_REQUIRED, state="bogus")
    resp = client.post("/incidents", json=payload)
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "state" in body["message"]


def test_create_incident_invalid_priority_returns_422(client):
    payload = dict(_REQUIRED, priority=9)
    resp = client.post("/incidents", json=payload)
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_create_incident_malformed_json_returns_400(client):
    resp = client.post(
        "/incidents", content=b"{not json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "MALFORMED_JSON"


def test_patch_incident_updates_given_fields_and_returns_200(client):
    created = client.post("/incidents", json=_REQUIRED).json()
    resp = client.patch(
        f"/incidents/{created['number']}",
        json={"state": "resolved", "priority": 1, "assigned_to": "dana", "assignment_group": "Support Tier 1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["state"] == "resolved"
    assert body["priority"] == 1
    assert body["assigned_to"] == "dana"
    assert body["assignment_group"] == "Support Tier 1"


def test_patch_incident_ignores_number_and_account_id_and_opened_at_in_body(client):
    created = client.post("/incidents", json=_REQUIRED).json()
    resp = client.patch(
        f"/incidents/{created['number']}",
        json={"number": "TICKET-999999", "account_id": "ACC-OTHER",
              "opened_at": "2000-01-01T00:00:00Z", "priority": 3},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["number"] == created["number"]
    assert body["account_id"] == created["account_id"]
    assert body["opened_at"] == created["opened_at"]
    assert body["priority"] == 3


def test_patch_incident_allows_resolving_with_no_business_rule_guard(client):
    # Preconditions: any actor may resolve any Incident regardless of open SLA breach or
    # unanswered customer — this HTTP layer adds no such guard (constitution Principle 5).
    created = client.post("/incidents", json=dict(_REQUIRED, state="new")).json()
    resp = client.patch(f"/incidents/{created['number']}", json={"state": "closed"})
    assert resp.status_code == 200
    assert resp.json()["state"] == "closed"


def test_patch_incident_invalid_state_returns_422_and_persists_no_change(client):
    created = client.post("/incidents", json=_REQUIRED).json()
    resp = client.patch(f"/incidents/{created['number']}", json={"state": "bogus"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "state" in body["message"]
    unchanged = client.get(f"/incidents/{created['number']}").json()
    assert unchanged["state"] == _REQUIRED["state"]


def test_patch_incident_invalid_priority_returns_422(client):
    created = client.post("/incidents", json=_REQUIRED).json()
    resp = client.patch(f"/incidents/{created['number']}", json={"priority": 9})
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"


def test_patch_incident_unknown_number_returns_404(client):
    resp = client.patch("/incidents/TICKET-999999", json={"priority": 2})
    assert resp.status_code == 404
    assert resp.json()["code"] == "INCIDENT_NOT_FOUND"
