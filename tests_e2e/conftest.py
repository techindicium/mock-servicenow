"""Session-scoped real-server fixture shared by this suite's own tests.

Tests that need a truly fresh, freshly-seeded database (BEH-1's fresh-seed assertion,
the discrepancy-presence test) call `start_itsm_api` directly with their own `tmp_path`
instead of this shared fixture, so no other test's writes contaminate the assertion.
"""
import socket

import pytest

from tests_e2e.browser import launch_chromium
from tests_e2e.servers import start_itsm_api, start_mcp_server


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("itsm-api-e2e")
    with start_itsm_api(tmp_path) as base_url:
        yield base_url


@pytest.fixture(scope="session")
def browser():
    """Session-scoped real Chromium browser, shared across all ui-e2e tests."""
    with launch_chromium() as browser:
        yield browser


@pytest.fixture
def page(browser):
    """Function-scoped browser context/tab — a fresh, isolated page per test."""
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def ui_app_server(tmp_path_factory) -> str:
    """Function-scoped real server, isolated from the shared session-scoped `server` fixture.

    Deliberately NOT `server` above: BEH-1's default-view assertion and BEH-6's ownerless-row
    assertion need a starting state this suite controls, and BEH-3/BEH-4's reload-persistence
    checks must not be confused by another suite's concurrent writes if tests ever run
    interleaved. A fresh function-scoped server (matching mock-jira's `ui_board_server`
    precedent) keeps each ui-e2e test's seeded starting state deterministic and independent of
    api-e2e's/mcp-e2e's tests in the same run.
    """
    tmp_path = tmp_path_factory.mktemp("ui-e2e")
    with start_itsm_api(tmp_path) as base_url:
        yield base_url


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def mcp_dual_server(tmp_path_factory) -> tuple[str, str]:
    """Session-scoped real itsm-api + real mcp-server pair, wired via API_BASE_URL.

    Shared across mcp-e2e.spec.md's BEH-1 through BEH-6. Tests that mutate shared state use
    unique, per-test-generated values (e.g. a UUID-suffixed short_description) to avoid
    cross-test collisions — there is no per-test database reset within this fixture's session
    scope. NOT used by BEH-7, which needs mcp-server running with no reachable upstream at all —
    see mcp_server_unreachable in this file.

    Yields: (api_base_url, mcp_base_url)
    """
    tmp_path = tmp_path_factory.mktemp("mcp-e2e-dual-server")
    with (
        start_itsm_api(tmp_path) as api_base_url,
        start_mcp_server(api_base_url) as mcp_base_url,
    ):
        yield api_base_url, mcp_base_url


@pytest.fixture
def mcp_server_unreachable() -> str:
    """Function-scoped: real mcp-server alone, API_BASE_URL pointed at a port nothing listens on.

    Deliberately NOT mcp_dual_server, per BEH-7's own dedicated-fixture requirement — no itsm-api
    process is started at all. Function-scoped since only the error-path tests need this
    topology.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        dead_port = probe.getsockname()[1]
    dead_api_base_url = f"http://127.0.0.1:{dead_port}"
    with start_mcp_server(dead_api_base_url) as mcp_base_url:
        yield mcp_base_url
