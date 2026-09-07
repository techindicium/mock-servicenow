def _create_incident(client, number="TICKET-000001"):
    # Assumes incident-lifecycle's POST /incidents exists; if incident numbers are
    # server-assigned rather than client-supplied by the time this plan is implemented,
    # replace this helper with a call to POST /incidents and capture the returned number.
    resp = client.post(
        "/incidents",
        json={
            "account_id": "ACCT-0001",
            "category": "network",
            "short_description": "Test incident",
            "description": "Created for work-notes test fixture",
            "state": "new",
            "priority": 3,
        },
    )
    return resp.json()["number"]


def test_list_work_notes_returns_paginated_chronological_items(client, conn):
    number = _create_incident(client)
    conn.execute(
        "INSERT INTO work_notes (sys_id, incident_number, created_at, created_by, note_type, body) "
        "VALUES ('INTERACTION-0000001', ?, '2026-09-07T10:00:00', 'customer', 'comment', 'First')",
        (number,),
    )
    conn.execute(
        "INSERT INTO work_notes (sys_id, incident_number, created_at, created_by, note_type, body) "
        "VALUES ('INTERACTION-0000002', ?, '2026-09-07T11:00:00', 'assist', 'work_note', 'Second')",
        (number,),
    )
    conn.commit()

    resp = client.get(f"/incidents/{number}/work_notes")
    assert resp.status_code == 200
    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] == 50
    assert body["total"] == 2
    assert [item["body"] for item in body["items"]] == ["First", "Second"]


def test_list_work_notes_unknown_incident_returns_404(client):
    resp = client.get("/incidents/TICKET-999999/work_notes")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "INCIDENT_NOT_FOUND"
    assert "TICKET-999999" in body["message"]


def test_post_work_note_returns_201_with_server_assigned_sys_id(client):
    number = _create_incident(client)
    resp = client.post(
        f"/incidents/{number}/work_notes",
        json={"created_by": "assist", "note_type": "work_note", "body": "Investigating"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["sys_id"].startswith("INTERACTION-")
    assert body["incident_number"] == number
    assert body["created_by"] == "assist"
    assert body["note_type"] == "work_note"
    assert body["body"] == "Investigating"
    assert body["created_at"]  # server-assigned, non-empty


def test_post_work_note_is_immediately_retrievable_via_get(client):
    number = _create_incident(client)
    post_resp = client.post(
        f"/incidents/{number}/work_notes",
        json={"created_by": "customer", "note_type": "comment", "body": "Thanks!"},
    )
    sys_id = post_resp.json()["sys_id"]
    list_resp = client.get(f"/incidents/{number}/work_notes")
    assert sys_id in [item["sys_id"] for item in list_resp.json()["items"]]


def test_post_work_note_accepts_any_created_by_with_no_authorship_check(client):
    number = _create_incident(client)
    for author in ("customer", "some.random.agent.name", "assist"):
        resp = client.post(
            f"/incidents/{number}/work_notes",
            json={"created_by": author, "note_type": "comment", "body": "x"},
        )
        assert resp.status_code == 201
        assert resp.json()["created_by"] == author


def test_post_work_note_does_not_mutate_parent_incident(client):
    number = _create_incident(client)
    before = client.get(f"/incidents/{number}").json()
    client.post(
        f"/incidents/{number}/work_notes",
        json={"created_by": "assist", "note_type": "state_change", "body": "Marked resolved"},
    )
    after = client.get(f"/incidents/{number}").json()
    assert before == after
