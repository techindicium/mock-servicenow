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
