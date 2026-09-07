import httpx


def test_unknown_incident_number_returns_404(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/incidents/TICKET-000000")
        assert resp.status_code == 404
        assert resp.json()["code"] == "INCIDENT_NOT_FOUND"


def test_unknown_escalation_number_returns_404(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/escalations/ESCALATION-0000")
        assert resp.status_code == 404
        assert resp.json()["code"] == "ESCALATION_NOT_FOUND"


def test_invalid_state_on_create_returns_422(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.post(
            "/incidents",
            json={
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": "bad state", "description": "e2e",
                "state": "not-a-real-state", "priority": 2,
            },
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"


def test_invalid_priority_on_patch_returns_422(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        incident = client.post(
            "/incidents",
            json={
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": "for patch", "description": "e2e",
                "state": "new", "priority": 2,
            },
        ).json()
        resp = client.patch(f"/incidents/{incident['number']}", json={"priority": 99})
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"


def test_invalid_note_type_returns_422(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        incident = client.post(
            "/incidents",
            json={
                "account_id": "ACCOUNT-1001", "category": "network",
                "short_description": "for note", "description": "e2e",
                "state": "new", "priority": 2,
            },
        ).json()
        resp = client.post(
            f"/incidents/{incident['number']}/work_notes",
            json={"created_by": "assist", "note_type": "not-a-real-type", "body": "x"},
        )
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"


def test_invalid_sla_definition_returns_422(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/sla", params={"sla_definition": "not-a-real-definition"})
        assert resp.status_code == 422
        assert resp.json()["code"] == "VALIDATION_ERROR"
