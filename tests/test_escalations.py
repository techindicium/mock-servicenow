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


def test_patch_escalation_updates_summary_owner_and_closed_at(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", summary="old", owner=None, closed_at=None)

    resp = client.patch(
        "/escalations/ESCALATION-0001",
        json={"summary": "new summary", "owner": "dana", "closed_at": "2026-03-01T00:00:00Z"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"] == "new summary"
    assert body["owner"] == "dana"
    assert body["closed_at"] == "2026-03-01T00:00:00Z"


def test_patch_escalation_ignores_immutable_fields_including_incident_number(client):
    conn = client.app.state.db_conn
    seed_escalation(
        conn, number="ESCALATION-0001", incident_number=None,
        account_id="ACC-1", opened_at="2026-01-01T00:00:00Z",
    )

    resp = client.patch(
        "/escalations/ESCALATION-0001",
        json={
            "number": "ESCALATION-9999",
            "account_id": "ACC-2",
            "opened_at": "2020-01-01T00:00:00Z",
            "incident_number": "TICKET-000999",
            "summary": "updated",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["number"] == "ESCALATION-0001"
    assert body["account_id"] == "ACC-1"
    assert body["opened_at"] == "2026-01-01T00:00:00Z"
    assert body["incident_number"] is None
    assert body["summary"] == "updated"


def test_patch_escalation_can_unassign_owner_with_explicit_null(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", owner="dana")

    resp = client.patch("/escalations/ESCALATION-0001", json={"owner": None})
    assert resp.status_code == 200
    assert resp.json()["owner"] is None


def test_patch_escalation_can_reopen_with_explicit_null_closed_at(client):
    conn = client.app.state.db_conn
    seed_escalation(conn, number="ESCALATION-0001", closed_at="2026-02-01T00:00:00Z")

    resp = client.patch("/escalations/ESCALATION-0001", json={"closed_at": None})
    assert resp.status_code == 200
    assert resp.json()["closed_at"] is None

    listing = client.get("/escalations?open_only=true").json()
    assert "ESCALATION-0001" in {item["number"] for item in listing["items"]}


def test_patch_escalation_unknown_number_returns_404(client):
    resp = client.patch("/escalations/ESCALATION-9999", json={"summary": "x"})
    assert resp.status_code == 404
    assert resp.json()["code"] == "ESCALATION_NOT_FOUND"


def test_patch_escalation_malformed_json_returns_400(client):
    resp = client.patch(
        "/escalations/ESCALATION-0001",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "MALFORMED_JSON"


def test_create_escalation_returns_201_with_server_assigned_fields(client):
    resp = client.post(
        "/escalations", json={"account_id": "ACC-1", "summary": "New escalation"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["number"].startswith("ESCALATION-")
    assert body["account_id"] == "ACC-1"
    assert body["summary"] == "New escalation"
    assert body["opened_at"] is not None
    assert body["incident_number"] is None
    assert body["owner"] is None
    assert body["closed_at"] is None


def test_create_escalation_stores_optional_incident_number_and_owner(client):
    resp = client.post(
        "/escalations",
        json={
            "account_id": "ACC-1",
            "summary": "New escalation",
            "incident_number": "TICKET-000123",
            "owner": "dana",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_number"] == "TICKET-000123"
    assert body["owner"] == "dana"


def test_create_escalation_ignores_closed_at_in_request_body(client):
    resp = client.post(
        "/escalations",
        json={
            "account_id": "ACC-1",
            "summary": "New escalation",
            "closed_at": "2026-01-01T00:00:00Z",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["closed_at"] is None


def test_create_escalation_missing_required_field_returns_422_and_creates_nothing(client):
    resp = client.post("/escalations", json={"summary": "No account"})
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "account_id" in body["message"]
    assert client.get("/escalations").json()["total"] == 0


def test_create_escalation_malformed_json_returns_400(client):
    resp = client.post(
        "/escalations",
        content=b"{not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "MALFORMED_JSON"
    assert client.get("/escalations").json()["total"] == 0


def test_create_escalation_immediately_visible_via_list_and_get(client):
    created = client.post(
        "/escalations", json={"account_id": "ACC-1", "summary": "New escalation"}
    ).json()
    number = created["number"]

    listing = client.get("/escalations").json()
    assert number in {item["number"] for item in listing["items"]}

    fetched = client.get(f"/escalations/{number}")
    assert fetched.status_code == 200
    assert fetched.json()["summary"] == "New escalation"
