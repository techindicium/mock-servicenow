def test_root_serves_incident_console_shell(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert 'id="nav-rail"' in body
    assert 'id="view-incidents"' in body
    assert 'id="incidents-table-body"' in body
    assert 'id="incident-record-view"' in body
    assert 'id="create-incident-form"' in body
    # This plan explicitly does not build nav-item markup — the sibling
    # escalations-directory-nav plan owns that (see incident-console.spec.md Task Map).
    assert "nav-item" not in body


def test_static_css_is_served(client):
    resp = client.get("/static/css/console.css")
    assert resp.status_code == 200


def test_static_js_is_served(client):
    resp = client.get("/static/js/incident-logic.js")
    assert resp.status_code == 200
    resp = client.get("/static/js/incident.js")
    assert resp.status_code == 200
