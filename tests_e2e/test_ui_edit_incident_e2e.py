"""Real-browser edit-incident e2e coverage (BEH-4, including the resolve-with-breach case).

Selectors match the actual implemented `static/index.html`/`static/js/incident.js`
(#edit-incident-form, #edit-state, #edit-priority, #record-fields) rather than
ui-e2e.plan.md's anticipated ones. Constitution Principle 5: no confirmation dialog, no
client-side transition guard — this suite intentionally never registers a Playwright dialog
handler, since none should ever fire.
"""

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def test_edit_incident_priority_persists_after_reload(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incident-list-view:not([hidden])")
    page.locator("#incidents-table-body tr").first.click()
    page.wait_for_selector("#incident-record-view:not([hidden])")

    number = page.locator("#record-number").inner_text()
    page.select_option("#edit-priority", "1")
    page.click("#edit-incident-form button[type=submit]")
    page.wait_for_selector("#record-fields dt:text-is('Priority') + dd:text-is('1')")

    page.reload()
    page.wait_for_selector("#incident-list-view:not([hidden])")
    page.locator(f'#incidents-table-body tr[data-number="{number}"]').click()
    page.wait_for_selector("#incident-record-view:not([hidden])")
    assert (
        page.locator("#record-fields dt:text-is('Priority') + dd").inner_text().strip()
        == "1"
    )


def test_resolve_incident_with_open_first_response_breach_saves_with_no_confirmation(
    page, ui_app_server
):
    # BEH-4: an Incident whose first_response TaskSla is breached can still be set to
    # resolved with no confirmation dialog intercepted (none exists to intercept — a
    # Playwright dialog listener that fires here would itself be a spec violation).
    page.goto(ui_app_server)
    page.wait_for_selector("#incident-list-view:not([hidden])")

    breach_found = False
    for state in ("new", "in_progress", "on_hold"):
        page.select_option("#filter-state", state)
        rows = page.locator("#incidents-table-body tr")
        try:
            page.wait_for_selector("#incidents-table-body tr", timeout=2000)
        except PlaywrightTimeoutError:
            continue  # no rows for this state filter — try the next one
        for i in range(rows.count()):
            rows.nth(i).click()
            page.wait_for_selector("#incident-record-view:not([hidden])")
            breached = page.locator(
                "#sla-table-body tr.sla-breached:has(td:text-is('first_response'))"
            )
            if breached.count() > 0:
                breach_found = True
                number = page.locator("#record-number").inner_text()
                page.select_option("#edit-state", "resolved")
                page.click("#edit-incident-form button[type=submit]")
                page.wait_for_selector(
                    "#record-fields dt:text-is('State') + dd:text-is('resolved')"
                )

                page.reload()
                page.wait_for_selector("#incident-list-view:not([hidden])")
                page.select_option("#filter-state", "resolved")
                page.locator(f'#incidents-table-body tr[data-number="{number}"]').click()
                page.wait_for_selector("#incident-record-view:not([hidden])")
                assert (
                    page.locator("#record-fields dt:text-is('State') + dd").inner_text().strip()
                    == "resolved"
                )
                break
            page.click("#back-to-list")
            page.wait_for_selector("#incident-list-view:not([hidden])")
        if breach_found:
            break

    assert breach_found, (
        "expected at least one un-resolved seeded Incident with a breached first_response "
        "TaskSla to exercise the resolve-with-open-breach transition"
    )
