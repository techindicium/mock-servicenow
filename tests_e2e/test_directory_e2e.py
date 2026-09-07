import httpx


def test_users_and_assignment_groups_over_real_http(server):
    with httpx.Client(base_url=server, timeout=5) as client:
        groups_resp = client.get("/assignment_groups")
        assert groups_resp.status_code == 200
        group_names = {g["name"] for g in groups_resp.json().get("items", groups_resp.json())}
        assert group_names == {"Support Tier 1", "Support Tier 2", "Solution Consultants"}

        users_resp = client.get("/users")
        assert users_resp.status_code == 200
        users = users_resp.json().get("items", users_resp.json())
        assert len(users) > 0
        for user in users:
            if user.get("assignment_group") is not None:
                assert user["assignment_group"] in group_names
