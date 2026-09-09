"""Reusable real-browser-process fixture for e2e suites.

Launches a real Chromium browser via Playwright's sync API (never headless-mocked, always a real
rendering engine) so ui-e2e's suite drives the actual served page — real clicks, real form fills —
never a UI JS module's functions directly. Wraps Playwright's own browser-launch failure (binary
not installed) into a clearly-named exception per ui-e2e.spec.md's E2E_BROWSER_NOT_INSTALLED
error case.

Modeled directly on mock-jira's tests_e2e/browser.py::launch_chromium.
"""
import contextlib
from collections.abc import Iterator

from playwright.sync_api import Browser, sync_playwright
from playwright.sync_api import Error as PlaywrightError


class E2EBrowserNotInstalled(RuntimeError):
    """Raised when Playwright's Chromium binary is not installed locally."""


@contextlib.contextmanager
def launch_chromium() -> Iterator[Browser]:
    """Launch a real headless Chromium browser; yield it. Closes it (and Playwright) on exit.

    Raises:
        E2EBrowserNotInstalled: Chromium's binary is missing locally. The message names the
            remedy (`playwright install chromium`) per ui-e2e.spec.md's E2E_BROWSER_NOT_INSTALLED
            error case.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError as exc:
            raise E2EBrowserNotInstalled(
                "Playwright's Chromium binary is not installed. Run `playwright install "
                f"chromium` once, then re-run this suite. Original error: {exc}"
            ) from exc
        try:
            yield browser
        finally:
            browser.close()
