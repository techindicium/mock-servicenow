"""Real-browser create-incident e2e coverage (BEH-5).

Selectors match the actual implemented `static/index.html`/`static/js/incident.js`
(#open-create-incident, #create-incident-form, #create-account_id, #create-category
[a plain text input, not a select], #create-short_description, #create-description,
#create-state, #create-priority) rather than ui-e2e.plan.md's anticipated ones.
"""
import uuid


def test_create_incident_form_navigates_to_new_record(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incident-list-view:not([hidden])")

    short_description = f"e2e-created incident {uuid.uuid4()}"
    page.click("#open-create-incident")
    page.wait_for_selector("#create-incident:not([hidden])")

    page.fill("#create-account_id", "ACCOUNT-1001")
    page.fill("#create-category", "network")
    page.fill("#create-short_description", short_description)
    page.fill("#create-description", "created by the ui e2e suite")
    page.select_option("#create-state", "new")
    page.select_option("#create-priority", "3")
    page.click("#create-incident-form button[type=submit]")

    page.wait_for_selector("#incident-record-view:not([hidden])")
    assert short_description in page.locator(
        "#record-fields dt:text-is('Short description') + dd"
    ).inner_text()
    assert "ACCOUNT-1001" in page.locator(
        "#record-fields dt:text-is('Account') + dd"
    ).inner_text()
