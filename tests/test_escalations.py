from tests.conftest import seed_escalation


def test_list_escalations_returns_paginated_page_including_null_fields(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", incident_number=None, owner=None)
    seed_escalation(conn, number="ESCALATION-0002", incident_number="TICKET-000123", owner="dana")

    resp = client.get("/escalations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["total"] == 2
    by_number = {item["number"]: item for item in body["items"]}
    assert set(by_number) == {"ESCALATION-0001", "ESCALATION-0002"}
    assert by_number["ESCALATION-0001"]["incident_number"] is None
    assert by_number["ESCALATION-0001"]["owner"] is None


def test_list_escalations_filtered_by_account_id(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", account_id="ACC-1")
    seed_escalation(conn, number="ESCALATION-0002", account_id="ACC-2")

    resp = client.get("/escalations?account_id=ACC-2")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["number"] == "ESCALATION-0002"


def test_list_escalations_open_only_excludes_closed(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", closed_at=None)
    seed_escalation(conn, number="ESCALATION-0002", closed_at="2026-02-01T00:00:00Z")

    resp = client.get("/escalations?open_only=true")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["number"] == "ESCALATION-0001"


def test_list_escalations_unknown_account_id_returns_200_empty_page(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", account_id="ACC-1")

    resp = client.get("/escalations?account_id=ACC-DOES-NOT-EXIST")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_list_escalations_invalid_open_only_returns_422(client):
    resp = client.get("/escalations?open_only=maybe")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "open_only" in body["message"]


def test_get_escalation_by_number_returns_full_representation_with_null_fields(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", incident_number=None, owner=None)

    resp = client.get("/escalations/ESCALATION-0001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["number"] == "ESCALATION-0001"
    assert body["incident_number"] is None
    assert body["owner"] is None


def test_get_escalation_unknown_number_returns_404(client):
    resp = client.get("/escalations/ESCALATION-9999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "ESCALATION_NOT_FOUND"
    assert "ESCALATION-9999" in body["message"]
