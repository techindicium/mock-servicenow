import httpx
import pytest

from tests_e2e.servers import E2EServerStartTimeout, start_itsm_api


def test_start_itsm_api_yields_reachable_seeded_base_url(tmp_path):
    with start_itsm_api(tmp_path) as base_url:
        resp = httpx.get(base_url + "/", timeout=5)
        assert resp.status_code == 200
        # Seeded before yielding — a fresh server must already carry fixture data.
        incidents = httpx.get(base_url + "/incidents", timeout=5).json()
        assert len(incidents.get("items", incidents)) > 0


def test_start_itsm_api_tears_down_process_on_exit(tmp_path):
    with start_itsm_api(tmp_path) as base_url:
        pass
    with pytest.raises(httpx.ConnectError):
        httpx.get(base_url + "/", timeout=1)


def test_start_itsm_api_raises_e2e_server_start_timeout_on_unhealthy_startup(tmp_path):
    not_a_dir = tmp_path / "not_a_directory"
    not_a_dir.write_text("this is a file, not a directory, so app startup fails fast")

    with pytest.raises(E2EServerStartTimeout) as exc_info, start_itsm_api(not_a_dir):
        pass  # pragma: no cover - should never be reached

    message = str(exc_info.value)
    assert "startup timeout" in message  # names the timeout
    assert "Last output" in message      # names the last-seen process output
