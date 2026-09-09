"""Real-browser coverage for BEH-10's Related Escalation panel.

Every seeded Escalation currently has `incident_number: null` (real fixture data generated from
course-shared's canon), so the "match found" branch cannot be exercised against real seeded data
today — only the "no related escalation" branch is reachable. Fabricated in-memory data covers
the match/multi-match logic exhaustively in tests_js/beh-10-related-escalation.test.js instead.
"""


def test_related_escalation_panel_shows_explicit_none_state(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector('#incidents-table-body tr[data-number]')
    page.locator("#incidents-table-body tr[data-number]").first.click()
    page.wait_for_selector("#incident-record-view:not([hidden])")

    page.wait_for_selector("#related-escalation-content")
    content = page.locator("#related-escalation-content").inner_text()
    assert "No related escalation" in content
