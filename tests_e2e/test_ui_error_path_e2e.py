"""Real-browser network-failure e2e coverage (BEH-8, E2E_UI_FETCH_FAILED).

Matches ui-e2e.plan.md Task 7 exactly — no selector adjustment needed. Route interception
(`page.route(...).abort("failed")`) is a real aborted network request at the browser's network
layer, not a mocked fetch, matching mock-jira's own ui-e2e.plan.md Task 7 precedent.
"""


def test_network_failure_shows_visible_error_message(page, ui_app_server):
    # Simulate the real server becoming unreachable mid-load by aborting the incidents
    # fetch at the network layer — no mocked fetch, a real aborted request.
    page.route("**/incidents*", lambda route: route.abort("failed"))

    page.goto(ui_app_server)

    page.wait_for_selector("#incidents-error:not([hidden])")
    error_text = page.locator("#incidents-error").inner_text()
    assert error_text.strip() != ""
