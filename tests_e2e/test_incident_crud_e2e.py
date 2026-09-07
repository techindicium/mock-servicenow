import httpx

from tests_e2e.servers import start_itsm_api


def test_fresh_seed_incidents_visible_over_real_http(tmp_path):
    # BEH-1: isolated fresh server, not the shared session fixture — this asserts
    # seed-then-serve, not just that some incident happens to exist.
    with start_itsm_api(tmp_path) as base_url:
        with httpx.Client(base_url=base_url, timeout=5) as client:
            resp = client.get("/incidents")
            assert resp.status_code == 200
            body = resp.json()
            items = body.get("items", body)
            assert len(items) > 0


def test_full_incident_lifecycle_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        created = client.post(
            "/incidents",
            json={
                "account_id": "ACCOUNT-1001",
                "category": "network",
                "short_description": "e2e incident",
                "description": "created by the e2e suite",
                "state": "new",
                "priority": 3,
            },
        )
        assert created.status_code == 201
        incident = created.json()
        number = incident["number"]
        assert incident["escalated"] is False
        assert incident["assigned_to"] is None

        fetched = client.get(f"/incidents/{number}")
        assert fetched.status_code == 200
        assert fetched.json()["number"] == number

        # ACCOUNT-1001 has hundreds of seeded incidents (real fixture volume, not just
        # the ten narrative tickets) and the new incident's server-assigned number
        # sorts last among them, so a large page_size is used to guarantee it is
        # visible on a single page rather than asserting on default pagination.
        listed = client.get(
            "/incidents", params={"account_id": "ACCOUNT-1001", "page_size": 1000}
        )
        assert any(i["number"] == number for i in listed.json().get("items", listed.json()))

        # BEH-8: unguarded patch — no permission/business-rule check on any transition.
        patched = client.patch(
            f"/incidents/{number}",
            json={
                "state": "resolved",
                "priority": 1,
                "assigned_to": "Rui Bastos",
                "assignment_group": "Support Tier 1",
            },
        )
        assert patched.status_code == 200
        updated = patched.json()
        assert updated["state"] == "resolved"
        assert updated["priority"] == 1
        assert updated["assigned_to"] == "Rui Bastos"
