"""Real-browser incident list/record render e2e coverage (BEH-1, BEH-2).

Selectors are drawn from the actual implemented `static/index.html`/`static/js/*.js` (see
incident-console.spec.md), not the ui-e2e.plan.md's anticipated ones — the plan's own
Architecture section authorizes adjusting locators while preserving behavioral intent.
"""


def test_incidents_view_renders_by_default_with_seeded_list(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#view-incidents:not([hidden])")
    page.wait_for_selector("#incident-list-view:not([hidden])")

    # Real DOM only — never a mocked fetch response.
    assert page.locator("#incidents-table-body tr").count() > 0


def test_opening_incident_renders_fields_work_notes_and_sla_panel(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incident-list-view:not([hidden])")

    page.locator("#incidents-table-body tr").first.click()
    page.wait_for_selector("#incident-record-view:not([hidden])")

    assert page.locator("#record-number").inner_text().strip() != ""
    assert page.locator(
        "#record-fields dt:text-is('Short description') + dd"
    ).count() == 1
    # Work-note timeline and SLA panel both render as part of the record view.
    page.wait_for_selector("#work-notes-timeline")
    page.wait_for_selector("#sla-panel")


def test_resolved_incident_with_breached_first_response_renders_as_fact(page, ui_app_server):
    # BEH-2: find a resolved Incident whose first_response TaskSla has_breached is true, by
    # walking the real rendered list/record views rather than querying the API directly —
    # everything this test reads comes from the DOM.
    page.goto(ui_app_server)
    page.wait_for_selector("#incident-list-view:not([hidden])")

    page.select_option("#filter-state", "resolved")
    page.wait_for_selector("#incidents-table-body tr")

    found_breach = False
    rows = page.locator("#incidents-table-body tr")
    for i in range(rows.count()):
        rows.nth(i).click()
        page.wait_for_selector("#incident-record-view:not([hidden])")
        breached = page.locator(
            "#sla-table-body tr.sla-breached:has(td:text-is('first_response'))"
        )
        if breached.count() > 0:
            found_breach = True
            # No error banner blocking the render — the breach is a plain, visible fact.
            assert page.locator("#incidents-error:not([hidden])").count() == 0
            break
        page.click("#back-to-list")
        page.wait_for_selector("#incident-list-view:not([hidden])")

    assert found_breach, (
        "expected at least one resolved Incident with a breached first_response TaskSla "
        "among the seeded, filtered rows — a load-bearing seeded discrepancy, not an error state"
    )
