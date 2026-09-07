"""Session-scoped real-server fixture shared by this suite's own tests.

Tests that need a truly fresh, freshly-seeded database (BEH-1's fresh-seed assertion,
the discrepancy-presence test) call `start_itsm_api` directly with their own `tmp_path`
instead of this shared fixture, so no other test's writes contaminate the assertion.
"""
import pytest

from tests_e2e.servers import start_itsm_api, start_mcp_server


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("itsm-api-e2e")
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
    with start_itsm_api(tmp_path) as api_base_url:
        with start_mcp_server(api_base_url) as mcp_base_url:
            yield api_base_url, mcp_base_url
