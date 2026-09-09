"""Real-browser create-escalation e2e coverage (BEH-6, BEH-7, BEH-8, BEH-9)."""
import uuid


def test_create_escalation_form_prepends_new_row(page, ui_app_server):
    page.goto(ui_app_server)
    page.click("#nav-escalations")
    page.wait_for_selector("#view-escalations:not([hidden])")

    summary = f"e2e-created escalation {uuid.uuid4()}"
    page.click("#open-create-escalation")
    page.wait_for_selector("#create-escalation:not([hidden])")

    page.fill("#create-escalation-account_id", "ACCOUNT-1001")
    page.fill("#create-escalation-summary", summary)
    page.click("#create-escalation-form button[type=submit]")

    page.wait_for_selector("#create-escalation", state="hidden")
    first_row_summary = page.locator("#escalations-table tbody tr").first.locator("td").nth(2).inner_text()
    assert first_row_summary == summary


def test_create_escalation_missing_required_field_shows_inline_error(page, ui_app_server):
    # BEH-8: client-side validation blocks the request entirely — no fetch is ever made.
    page.goto(ui_app_server)
    page.click("#nav-escalations")
    page.wait_for_selector("#view-escalations:not([hidden])")
    page.click("#open-create-escalation")
    page.wait_for_selector("#create-escalation:not([hidden])")

    page.fill("#create-escalation-summary", "missing account id")
    page.click("#create-escalation-form button[type=submit]")

    page.wait_for_selector("#create-escalation-error:not([hidden])")
    error = page.locator("#create-escalation-error")
    assert "account_id" in error.inner_text()
    # form stays open and retains the entered value
    assert page.input_value("#create-escalation-summary") == "missing account id"


def test_create_escalation_network_failure_shows_error_and_retains_form(page, ui_app_server):
    # BEH-9: a genuine POST /escalations failure — a real aborted network request at the
    # browser's network layer (page.route(...).abort), not a mocked fetch, matching
    # tests_e2e/test_ui_error_path_e2e.py's precedent. Client-side validation passes here;
    # the request is actually sent and then fails.
    page.goto(ui_app_server)
    page.click("#nav-escalations")
    page.wait_for_selector("#view-escalations:not([hidden])")
    page.click("#open-create-escalation")
    page.wait_for_selector("#create-escalation:not([hidden])")

    page.route("**/escalations", lambda route: route.abort("failed"))

    page.fill("#create-escalation-account_id", "ACCOUNT-1001")
    page.fill("#create-escalation-summary", "will fail to save")
    page.click("#create-escalation-form button[type=submit]")

    page.wait_for_selector("#create-escalation-error:not([hidden])")
    error = page.locator("#create-escalation-error")
    assert error.inner_text().strip() != ""
    # the form stays open (not hidden) and the entered values are retained, not cleared
    assert page.locator("#create-escalation").is_visible()
    assert page.input_value("#create-escalation-account_id") == "ACCOUNT-1001"
    assert page.input_value("#create-escalation-summary") == "will fail to save"
