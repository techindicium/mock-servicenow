"""Real-browser add-work-note e2e coverage (BEH-3).

Selectors match the actual implemented `static/index.html`/`static/js/incident.js`
(#add-work-note-form, #note-created_by, #note-note_type, #note-body,
#work-notes-timeline) rather than ui-e2e.plan.md's anticipated ones.
"""
import uuid


def test_add_work_note_appears_in_timeline_and_survives_reload(page, ui_app_server):
    page.goto(ui_app_server)
    page.wait_for_selector("#incident-list-view:not([hidden])")
    page.locator("#incidents-table-body tr").first.click()
    page.wait_for_selector("#incident-record-view:not([hidden])")

    number = page.locator("#record-number").inner_text()

    note_body = f"e2e note {uuid.uuid4()}"
    page.fill("#note-created_by", "assist")
    page.select_option("#note-note_type", "comment")
    page.fill("#note-body", note_body)
    page.click("#add-work-note-form button[type=submit]")

    # No page reload — the new note is visible immediately.
    page.wait_for_selector(f'#work-notes-timeline li:has-text("{note_body}")')

    # BEH-3: verified by reloading the page in the same real browser.
    page.reload()
    page.wait_for_selector("#incident-list-view:not([hidden])")
    page.locator(f'#incidents-table-body tr[data-number="{number}"]').click()
    page.wait_for_selector("#incident-record-view:not([hidden])")
    page.wait_for_selector(f'#work-notes-timeline li:has-text("{note_body}")')
