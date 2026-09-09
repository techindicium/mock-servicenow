import httpx


def test_dashboard_renders_seven_tiles_with_real_counts(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incidents-table-body tr")
    page.click("#nav-dashboard")
    page.wait_for_selector('.dashboard-tile[data-tile="new"] .dashboard-tile-value')

    assert page.locator(".dashboard-tile").count() == 7

    expected_total = httpx.get(
        f"{ui_app_server}/incidents", params={"state": "new", "page_size": 1}
    ).json()["total"]
    actual = page.locator('.dashboard-tile[data-tile="new"] .dashboard-tile-value').inner_text()
    assert actual == str(expected_total)


def test_breached_sla_tile_is_plain_text_with_no_click_affordance(page, ui_app_server):
    page.goto(ui_app_server)
    page.click("#nav-dashboard")
    page.wait_for_selector('.dashboard-tile[data-tile="breached_sla"] .dashboard-tile-value')

    tag_name = page.locator(
        '.dashboard-tile[data-tile="breached_sla"] .dashboard-tile-value'
    ).evaluate("el => el.tagName")
    assert tag_name == "SPAN"


def test_clicking_a_state_tile_navigates_to_a_correctly_filtered_incidents_view(page, ui_app_server):
    page.goto(ui_app_server)
    page.click("#nav-dashboard")
    page.wait_for_selector('.dashboard-tile[data-tile="closed"] .dashboard-tile-value')
    page.click('.dashboard-tile[data-tile="closed"] .dashboard-tile-value')

    page.wait_for_selector("#incident-list-view:not([hidden])")
    assert page.locator("#filter-state").input_value() == "closed"
    page.wait_for_selector('#incidents-table-body tr[data-state="closed"]')
    # Every rendered row is really closed — the filter was actually applied, not just the select's value
    states = page.locator("#incidents-table-body tr").evaluate_all(
        "rows => rows.map(r => r.dataset.state)"
    )
    assert all(s == "closed" for s in states)
