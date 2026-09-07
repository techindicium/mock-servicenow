import socket

import pytest

from tests_e2e.servers import E2EServerStartTimeout, start_itsm_api, start_mcp_server


def test_start_mcp_server_yields_reachable_base_url(tmp_path):
    with start_itsm_api(tmp_path) as api_base_url:
        with start_mcp_server(api_base_url) as mcp_base_url:
            host, port = mcp_base_url.replace("http://", "").split(":")
            with socket.create_connection((host, int(port)), timeout=2):
                pass  # connection accepted — process is up


def test_start_mcp_server_tears_down_process_on_exit(tmp_path):
    with start_itsm_api(tmp_path) as api_base_url:
        with start_mcp_server(api_base_url) as mcp_base_url:
            pass
        host, port = mcp_base_url.replace("http://", "").split(":")
        with pytest.raises(OSError):
            with socket.create_connection((host, int(port)), timeout=1):
                pass  # pragma: no cover - should never be reached


def test_start_mcp_server_raises_e2e_server_start_timeout_on_bad_command(monkeypatch, tmp_path):
    # Deliberate misuse: make _free_port() return a non-numeric value, so mcp_server/server.py's
    # `int(os.environ["PORT"])` raises ValueError and the subprocess exits almost immediately —
    # exercising the "process exited early" branch of E2E_SERVER_START_TIMEOUT without waiting
    # out the full startup timeout.
    #
    # NOT a busy-port trick: start_mcp_server's health check is a bare TCP connect, so binding a
    # blocker socket on the target port would make the health check falsely report success
    # against the blocker itself, never actually forcing (or detecting) a real bind failure in
    # the mcp-server subprocess — mirrors mock-jira/tests_e2e/test_mcp_server_fixture.py's own
    # documented reasoning for the same test.
    with start_itsm_api(tmp_path) as api_base_url:
        monkeypatch.setattr("tests_e2e.servers._free_port", lambda: "not-a-port-number")
        with pytest.raises(E2EServerStartTimeout) as exc_info, start_mcp_server(api_base_url):
            pass  # pragma: no cover - should never be reached
        message = str(exc_info.value)
        assert "startup timeout" in message
        assert "Last output" in message
