import httpx


def _all_pages(client, path, **params):
    # Canonical envelope (incident-lifecycle.plan.md Task 1) is
    # {"items", "page", "page_size", "total"} — no "has_more" field — so pagination
    # continues while fewer rows have been seen than "total".
    items = []
    page = 1
    while True:
        resp = client.get(path, params={**params, "page": page})
        body = resp.json()
        page_items = body["items"]
        if not page_items:
            break
        items.extend(page_items)
        if len(items) >= body["total"]:
            break
        page += 1
        if page > 500:
            raise AssertionError(f"pagination over {path} did not terminate")
    return items


def test_sla_business_hours_wall_clock_discrepancy_present(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resolution_records = _all_pages(client, "/sla", sla_definition="resolution")
        assert len(resolution_records) > 0, "E2E_DISCREPANCY_MISSING: no resolution SLA records"
        assert all(r["business_time_only"] is True for r in resolution_records), (
            "E2E_DISCREPANCY_MISSING: SLA business-hours/wall-clock discrepancy — "
            "expected every resolution-definition record to have business_time_only: true"
        )


def test_two_ownerless_escalations_present(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        escalations = _all_pages(client, "/escalations")
        ownerless = [e for e in escalations if e["owner"] is None]
        assert len(ownerless) >= 2, (
            "E2E_DISCREPANCY_MISSING: expected at least two ownerless Escalations "
            f"(owner: null), found {len(ownerless)}"
        )


def test_resolved_incident_with_open_first_response_breach_present(server):
    # Third discrepancy (review note SA-1): a resolved/closed Incident whose
    # first_response TaskSla still shows has_breached: true.
    with httpx.Client(base_url=server, timeout=5) as client:
        breached_first_response = _all_pages(
            client, "/sla", sla_definition="first_response", breached="true"
        )
        assert len(breached_first_response) > 0, (
            "E2E_DISCREPANCY_MISSING: no breached first_response SLA records at all"
        )

        breached_incident_numbers = {r["incident_number"] for r in breached_first_response}
        found = False
        for number in breached_incident_numbers:
            incident = client.get(f"/incidents/{number}").json()
            if incident["state"] in ("resolved", "closed"):
                found = True
                break

        assert found, (
            "E2E_DISCREPANCY_MISSING: expected at least one resolved-or-closed Incident "
            "whose first_response TaskSla still has_breached: true"
        )
