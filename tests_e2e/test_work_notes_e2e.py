import httpx


def test_work_notes_list_and_add_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        incident = client.post(
            "/incidents",
            json={
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": "e2e work note incident",
                "description": "for work-note e2e coverage",
                "state": "new", "priority": 2,
            },
        ).json()
        number = incident["number"]

        # BEH-4: unguarded authorship — accepts "assist" with no check.
        created = client.post(
            f"/incidents/{number}/work_notes",
            json={"created_by": "assist", "note_type": "comment", "body": "e2e note"},
        )
        assert created.status_code == 201
        note = created.json()
        assert note["incident_number"] == number
        assert "sys_id" in note

        listed = client.get(f"/incidents/{number}/work_notes")
        assert listed.status_code == 200
        notes = listed.json().get("items", listed.json())
        assert any(n["sys_id"] == note["sys_id"] for n in notes)

        # Posting a work note never mutates the parent Incident's state.
        still_new = client.get(f"/incidents/{number}").json()
        assert still_new["state"] == "new"
