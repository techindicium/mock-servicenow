from pathlib import Path

INDEX_HTML = Path("static/index.html")


def test_index_html_references_nav_rail_files():
    html = INDEX_HTML.read_text()
    assert '<link rel="stylesheet" href="/static/css/nav.css">' in html
    for script in (
        "ui-errors.js",
        "nav-logic.js",
        "nav.js",
        "escalations-logic.js",
        "escalations.js",
        "directory-logic.js",
        "directory.js",
    ):
        assert f'/static/js/{script}"' in html


def test_index_html_contains_nav_rail_and_three_view_containers():
    html = INDEX_HTML.read_text()
    assert '<nav class="nav-rail"' in html
    assert 'id="nav-incidents"' in html
    assert 'id="nav-escalations"' in html
    assert 'id="nav-directory"' in html
    assert 'id="view-incidents" class="view">' in html
    assert 'id="view-escalations" class="view" hidden>' in html
    assert 'id="view-directory" class="view" hidden>' in html


def test_nav_rail_css_and_js_files_exist():
    assert Path("static/css/nav.css").is_file()
    for script in (
        "ui-errors.js",
        "nav-logic.js",
        "nav.js",
        "escalations-logic.js",
        "escalations.js",
        "directory-logic.js",
        "directory.js",
    ):
        assert Path(f"static/js/{script}").is_file()
