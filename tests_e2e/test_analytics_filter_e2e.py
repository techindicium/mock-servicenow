import httpx


def _all_incident_numbers(client, **params):
    # The canonical envelope (incident-lifecycle.plan.md Task 1) is
    # {"items", "page", "page_size", "total"} — no "has_more" field — so pagination
    # continues while fewer rows have been seen than "total". ACCOUNT-1001 alone has
    # hundreds of seeded incidents, well past the default page_size of 50, so a
    # single-page fetch would silently under-count both sides of this comparison.
    numbers = set()
    seen = 0
    page = 1
    while True:
        resp = client.get("/incidents", params={**params, "page": page})
        body = resp.json()
        items = body["items"]
        if not items:
            break
        numbers.update(i["number"] for i in items)
        seen += len(items)
        if seen >= body["total"]:
            break
        page += 1
        if page > 200:  # safety valve against an unbounded loop
            raise AssertionError("pagination did not terminate")
    return numbers


def test_account_and_opened_after_filter_matches_independent_fixture_filtering(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        filtered_resp = client.get(
            "/incidents",
            params={"account_id": "ACCOUNT-1001", "opened_after": "2026-08-01"},
        )
        assert filtered_resp.status_code == 200
        filtered_numbers = _all_incident_numbers(
            client, account_id="ACCOUNT-1001", opened_after="2026-08-01"
        )

        # Independently filter the same seeded data by paging through the full,
        # unfiltered set and applying the same predicate in Python — the same way
        # the analytics warehouse would compute this set from a raw extract. The
        # canonical envelope (incident-lifecycle.plan.md Task 1) is
        # {"items", "page", "page_size", "total"} — no "has_more" field — so
        # pagination continues while fewer rows have been seen than "total".
        expected_numbers = set()
        seen = 0
        page = 1
        while True:
            page_resp = client.get(
                "/incidents", params={"account_id": "ACCOUNT-1001", "page": page}
            )
            body = page_resp.json()
            items = body["items"]
            if not items:
                break
            for incident in items:
                if incident["opened_at"] >= "2026-08-01":
                    expected_numbers.add(incident["number"])
            seen += len(items)
            if seen >= body["total"]:
                break
            page += 1
            if page > 200:  # safety valve against an unbounded loop
                raise AssertionError("pagination did not terminate")

        assert filtered_numbers == expected_numbers
