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
