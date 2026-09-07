from tests.conftest import seed_task_sla


def test_get_sla_unfiltered_returns_paginated_page_of_all_records(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", incident_number="TICKET-000001")
    seed_task_sla(conn, sys_id="SLA-0002", incident_number="TICKET-000002")

    resp = client.get("/sla")

    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert {item["sys_id"] for item in body["items"]} == {"SLA-0001", "SLA-0002"}


def test_get_sla_filtered_by_incident_number_returns_matching_records_only(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", incident_number="TICKET-000001",
                  sla_definition="first_response")
    seed_task_sla(conn, sys_id="SLA-0002", incident_number="TICKET-000001",
                  sla_definition="resolution")
    seed_task_sla(conn, sys_id="SLA-0003", incident_number="TICKET-000002")

    resp = client.get("/sla?incident_number=TICKET-000001")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert {item["sys_id"] for item in body["items"]} == {"SLA-0001", "SLA-0002"}


def test_get_sla_unknown_incident_number_returns_200_with_empty_paginated_envelope(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", incident_number="TICKET-000001")

    resp = client.get("/sla?incident_number=TICKET-999999")

    assert resp.status_code == 200
    body = resp.json()
    # SA-1: the full paginated envelope, never a bare [] — "empty array" in the spec refers only
    # to the items field's value.
    assert body == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_get_sla_filtered_by_breached_true(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", has_breached=1)
    seed_task_sla(conn, sys_id="SLA-0002", has_breached=0)

    resp = client.get("/sla?breached=true")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["sys_id"] == "SLA-0001"
    assert body["items"][0]["has_breached"] is True


def test_get_sla_filtered_by_breached_false(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", has_breached=1)
    seed_task_sla(conn, sys_id="SLA-0002", has_breached=0)

    resp = client.get("/sla?breached=false")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["sys_id"] == "SLA-0002"


def test_get_sla_invalid_breached_value_returns_422(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001")

    resp = client.get("/sla?breached=maybe")

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "breached" in body["message"]


def test_get_sla_filtered_by_sla_definition_first_response(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", sla_definition="first_response")
    seed_task_sla(conn, sys_id="SLA-0002", sla_definition="resolution")

    resp = client.get("/sla?sla_definition=first_response")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["sys_id"] == "SLA-0001"


def test_get_sla_filtered_by_sla_definition_resolution(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001", sla_definition="first_response")
    seed_task_sla(conn, sys_id="SLA-0002", sla_definition="resolution")

    resp = client.get("/sla?sla_definition=resolution")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["sys_id"] == "SLA-0002"


def test_get_sla_invalid_sla_definition_value_returns_422_naming_allowed_values(client, conn):
    seed_task_sla(conn, sys_id="SLA-0001")

    resp = client.get("/sla?sla_definition=escalation_response")

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "sla_definition" in body["message"]
    assert "first_response" in body["message"] and "resolution" in body["message"]
