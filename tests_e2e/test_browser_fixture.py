import pytest

from tests_e2e.browser import E2EBrowserNotInstalled, launch_chromium


def test_launch_chromium_yields_a_working_browser(ui_app_server):
    with launch_chromium() as browser:
        page = browser.new_page()
        page.goto(ui_app_server)
        assert page.title() != ""
        page.close()


def test_launch_chromium_wraps_missing_binary_error(monkeypatch):
    from playwright.sync_api import Error as PlaywrightError

    class _FakeChromium:
        def launch(self):
            raise PlaywrightError(
                "Executable doesn't exist at .../chromium-1234/chrome-linux/chrome\n"
                "Looks like Playwright was just installed or updated.\n"
                "Please run the following command to download new browsers:\n"
                "    playwright install"
            )

    class _FakePlaywrightContext:
        chromium = _FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    monkeypatch.setattr(
        "tests_e2e.browser.sync_playwright", lambda: _FakePlaywrightContext()
    )

    with pytest.raises(E2EBrowserNotInstalled) as exc_info, launch_chromium():
        pass  # pragma: no cover - should never be reached

    assert "playwright install chromium" in str(exc_info.value)
