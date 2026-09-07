def test_create_schema_creates_sys_user_and_assignment_group_tables(conn):
    conn.execute(
        "INSERT INTO assignment_group (name) VALUES (?)", ("Support Tier 1",)
    )
    conn.execute(
        "INSERT INTO sys_user (name, role, assignment_group) VALUES (?, ?, ?)",
        ("Rui Bastos", "Support Manager", None),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM sys_user WHERE name = ?", ("Rui Bastos",)).fetchone()
    assert row["role"] == "Support Manager"
    assert row["assignment_group"] is None


def test_paginate_rows_slices_and_reports_total():
    from app.pagination import paginate_rows

    rows = list(range(1, 11))
    items, total = paginate_rows(rows, page=2, page_size=4)
    assert items == [5, 6, 7, 8]
    assert total == 10


def test_list_assignment_groups_returns_exactly_the_three_named_groups(client, conn):
    for name in ("Support Tier 1", "Support Tier 2", "Solution Consultants"):
        conn.execute("INSERT INTO assignment_group (name) VALUES (?)", (name,))
    conn.commit()

    resp = client.get("/assignment_groups")

    assert resp.status_code == 200
    body = resp.json()
    names = {g["name"] for g in body["items"]}
    assert names == {"Support Tier 1", "Support Tier 2", "Solution Consultants"}
    assert body["total"] == 3


def _seed_directory(conn):
    for name in ("Support Tier 1", "Support Tier 2", "Solution Consultants"):
        conn.execute("INSERT INTO assignment_group (name) VALUES (?)", (name,))
    conn.execute(
        "INSERT INTO sys_user (name, role, assignment_group) VALUES (?, ?, ?)",
        ("Rui Bastos", "Support Manager", None),
    )
    conn.execute(
        "INSERT INTO sys_user (name, role, assignment_group) VALUES (?, ?, ?)",
        ("Priya Nair", "Solution Consultant", "Solution Consultants"),
    )
    conn.execute(
        "INSERT INTO sys_user (name, role, assignment_group) VALUES (?, ?, ?)",
        ("Joao Pinto", "Support Engineer", "Support Tier 1"),
    )
    conn.commit()


def test_list_users_returns_full_seeded_directory(client, conn):
    _seed_directory(conn)

    resp = client.get("/users")

    assert resp.status_code == 200
    body = resp.json()
    names = {u["name"] for u in body["items"]}
    assert names == {"Rui Bastos", "Priya Nair", "Joao Pinto"}
    assert body["total"] == 3


def test_every_user_group_membership_names_a_known_assignment_group(client, conn):
    _seed_directory(conn)
    valid_groups = {"Support Tier 1", "Support Tier 2", "Solution Consultants"}

    resp = client.get("/users")

    for user in resp.json()["items"]:
        if user["assignment_group"] is not None:
            assert user["assignment_group"] in valid_groups


def test_users_page_shape_returns_all_rows_in_one_page_by_default(client, conn):
    _seed_directory(conn)

    resp = client.get("/users")

    body = resp.json()
    assert body["page"] == 1
    assert body["page_size"] >= body["total"]
    assert len(body["items"]) == body["total"]


def test_assignment_groups_page_shape_returns_all_rows_in_one_page_by_default(client, conn):
    for name in ("Support Tier 1", "Support Tier 2", "Solution Consultants"):
        conn.execute("INSERT INTO assignment_group (name) VALUES (?)", (name,))
    conn.commit()

    resp = client.get("/assignment_groups")

    body = resp.json()
    assert body["page"] == 1
    assert len(body["items"]) == body["total"] == 3


def test_get_users_with_non_integer_page_returns_422_validation_error(client):
    resp = client.get("/users", params={"page": "not-a-number"})

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "page" in body["message"]


def test_get_assignment_groups_with_non_integer_page_size_returns_422_validation_error(client):
    resp = client.get("/assignment_groups", params={"page_size": "lots"})

    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "page_size" in body["message"]
