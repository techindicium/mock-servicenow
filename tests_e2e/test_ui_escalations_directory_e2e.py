"""Real-browser Escalations/Directory view e2e coverage (BEH-6, BEH-7).

Selectors match the actual implemented `static/index.html`/`static/js/escalations.js`/
`static/js/directory.js` (#nav-escalations, #nav-directory, #view-escalations,
#view-directory, #escalations-table, #users-table, #assignment-groups-table) rather than
ui-e2e.plan.md's anticipated ones. Constitution Principle 6: an ownerless Escalation renders
as an explicit "Unassigned" fact (with an `owner-unassigned` class on that cell), never
hidden or defaulted away.
"""


def test_escalations_view_renders_including_ownerless_row(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#view-incidents:not([hidden])")

    page.click("#nav-escalations")
    page.wait_for_selector("#view-escalations:not([hidden])")
    assert page.locator("#view-incidents").is_hidden()

    page.wait_for_selector("#escalations-table tbody tr")
    assert page.locator("#escalations-table tbody tr").count() > 0
    # BEH-6: an ownerless Escalation rendered as an explicit unassigned state, read
    # from the actual DOM — a seeded discrepancy, not an error the UI hides.
    ownerless = page.locator("#escalations-table tbody tr:has(td.owner-unassigned)")
    assert ownerless.count() >= 1


def test_directory_view_renders_users_and_assignment_groups(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#view-incidents:not([hidden])")

    page.click("#nav-directory")
    page.wait_for_selector("#view-directory:not([hidden])")
    assert page.locator("#view-escalations").is_hidden()
    assert page.locator("#view-incidents").is_hidden()

    page.wait_for_selector("#users-table tbody tr")
    page.wait_for_selector("#assignment-groups-table tbody tr")
    assert page.locator("#users-table tbody tr").count() > 0
    assert page.locator("#assignment-groups-table tbody tr").count() > 0
