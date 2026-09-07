import httpx


def test_ownerless_escalations_read_correctly_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/escalations")
        assert resp.status_code == 200
        escalations = resp.json().get("items", resp.json())
        assert len(escalations) > 0

        ownerless = [e for e in escalations if e["owner"] is None]
        assert len(ownerless) >= 1, (
            "expected at least one seeded ownerless Escalation (owner: null) — "
            "this is a load-bearing seeded discrepancy, not an error state"
        )

        one = client.get(f"/escalations/{ownerless[0]['number']}")
        assert one.status_code == 200
        assert one.json()["owner"] is None


def test_open_only_filter_excludes_closed_escalations(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        open_ones = client.get("/escalations", params={"open_only": "true"}).json()
        items = open_ones.get("items", open_ones)
        assert all(e["closed_at"] is None for e in items)
