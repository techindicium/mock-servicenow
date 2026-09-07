import httpx

from tests_e2e.breached_sla_fixture import ensure_breached_unresolved_incident


def test_ensure_breached_unresolved_incident_returns_a_valid_open_incident(mcp_dual_server):
    api_base_url, _ = mcp_dual_server

    number = ensure_breached_unresolved_incident(api_base_url)

    with httpx.Client(base_url=api_base_url, timeout=5) as http_client:
        incident = http_client.get(f"/incidents/{number}").json()
        sla_records = http_client.get(f"/sla?incident_number={number}").json()["items"]

    assert incident["state"] not in ("resolved", "closed")
    first_response = next(s for s in sla_records if s["sla_definition"] == "first_response")
    assert first_response["has_breached"] is True
