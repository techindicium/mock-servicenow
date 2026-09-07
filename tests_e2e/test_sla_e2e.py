import httpx


def test_business_time_only_resolution_records_read_correctly_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/sla", params={"sla_definition": "resolution"})
        assert resp.status_code == 200
        records = resp.json().get("items", resp.json())
        assert len(records) > 0
        # Per sla-records.spec.md BEH-7: true for every resolution-definition record.
        assert all(r["business_time_only"] is True for r in records)


def test_unknown_incident_number_filter_returns_empty_array_not_404(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/sla", params={"incident_number": "TICKET-999999999"})
        assert resp.status_code == 200
        assert resp.json().get("items", resp.json()) == []
