import httpx

EXPECTED_PATHS = {
    "/", "/incidents", "/incidents/{number}",
    "/incidents/{number}/work_notes",
    "/escalations", "/escalations/{number}",
    "/sla", "/users", "/assignment_groups",
}


def test_openapi_json_lists_every_implemented_route_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        doc = resp.json()
        documented_paths = set(doc["paths"].keys())
        missing = EXPECTED_PATHS - documented_paths
        assert not missing, f"OpenAPI document is missing routes: {missing}"
