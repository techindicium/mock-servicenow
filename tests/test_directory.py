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
