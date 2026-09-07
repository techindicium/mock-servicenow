"""Session-scoped real-server fixture shared by this suite's own tests.

Tests that need a truly fresh, freshly-seeded database (BEH-1's fresh-seed assertion,
the discrepancy-presence test) call `start_itsm_api` directly with their own `tmp_path`
instead of this shared fixture, so no other test's writes contaminate the assertion.
"""
import pytest

from tests_e2e.servers import start_itsm_api


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("itsm-api-e2e")
    with start_itsm_api(tmp_path) as base_url:
        yield base_url
