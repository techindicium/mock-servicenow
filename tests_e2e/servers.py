"""Reusable real-server-process fixture for e2e suites.

Launches `uvicorn app.main:app` as its own OS process (never imported in-process),
on an ephemeral local port, with `DATABASE_PATH` pointed at a fresh temp file. Before
starting the API process, runs the documented seed command (`python -m app.seed`) as
its own subprocess call against that same temp file, per fixture-seeding.plan.md's
explicit design decision that seeding is never wired into app startup. Polls
`GET /` (the app's existing root/health route) until it answers 200, then yields the
base URL. Terminates the process on exit.

Modeled directly on mock-jira's `tests_e2e/servers.py::start_issue_tracker_api`.
Kept free of any pytest dependency so it can be reused directly by any future
e2e-shaped spec in this repo.
"""
import contextlib
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx

_STARTUP_TIMEOUT_SECONDS = 10.0
_POLL_INTERVAL_SECONDS = 0.1


class E2EServerStartTimeout(RuntimeError):
    """Raised when the server subprocess doesn't answer GET / within the startup timeout."""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def start_itsm_api(tmp_path: Path) -> Iterator[str]:
    """Start the real itsm-api server as a subprocess; yield its base_url.

    Args:
        tmp_path: a directory to place this run's SQLite DB file in. Callers control
            scope (function- or session-level) by choosing what Path they pass in
            (e.g. pytest's `tmp_path` vs. `tmp_path_factory.mktemp(...)`).

    Yields:
        The base URL (e.g. "http://127.0.0.1:54231") once the server answers GET /,
        with the fixture data already seeded.

    Raises:
        E2EServerStartTimeout: the seed command failed to run against `tmp_path`, or
            the server process didn't answer GET / within the startup timeout. The
            exception message names the timeout and the last-seen process output
            (E2E_SERVER_START_TIMEOUT in api-e2e.spec.md).
    """
    port = _free_port()
    db_path = Path(tmp_path) / "e2e.db"
    base_url = f"http://127.0.0.1:{port}"
    # Both app/main.py and app/seed.py's main() read DATABASE_PATH, so the seed command
    # and the live server agree on which database file they're each pointed at.
    env = {**os.environ, "DATABASE_PATH": str(db_path)}

    seed_result = subprocess.run(
        [sys.executable, "-m", "app.seed"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if seed_result.returncode != 0:
        raise E2EServerStartTimeout(
            f"seed command `python -m app.seed` failed (exit code "
            f"{seed_result.returncode}) before the server could start against "
            f"{db_path}, within the {_STARTUP_TIMEOUT_SECONDS}s startup timeout. "
            f"Last output:\n{seed_result.stdout}{seed_result.stderr}"
        )

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app.main:app",
            "--host", "127.0.0.1", "--port", str(port),
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + _STARTUP_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                last_output = proc.stdout.read() if proc.stdout else ""
                raise E2EServerStartTimeout(
                    f"server process exited early (code {proc.returncode}) before "
                    f"answering GET {base_url}/ within the {_STARTUP_TIMEOUT_SECONDS}s "
                    f"startup timeout. Last output:\n{last_output}"
                )
            try:
                resp = httpx.get(base_url + "/", timeout=1)
                if resp.status_code == 200:
                    break
            except httpx.TransportError:
                pass
            time.sleep(_POLL_INTERVAL_SECONDS)
        else:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            last_output = proc.stdout.read() if proc.stdout else ""
            raise E2EServerStartTimeout(
                f"server did not answer GET {base_url}/ within the "
                f"{_STARTUP_TIMEOUT_SECONDS}s startup timeout. Last output:\n{last_output}"
            )
        yield base_url
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


@contextlib.contextmanager
def start_mcp_server(api_base_url: str) -> Iterator[str]:
    """Start the real mcp-server process as a subprocess; yield its base_url.

    Args:
        api_base_url: value to set API_BASE_URL to — a live itsm-api's base_url in the normal
            (dual-server) topology, or a deliberately unreachable URL for mcp-e2e.spec.md's
            BEH-7 scenario (a dedicated caller uses this same helper for that; see
            mcp_server_unreachable in tests_e2e/conftest.py).

    Yields:
        mcp-server's own base URL (e.g. "http://127.0.0.1:54232"). This is NOT the MCP endpoint
        URL — callers append the SDK's default streamable-http path themselves (see
        tests_e2e/mcp_client.py::connect).

    Raises:
        E2EServerStartTimeout: the process's port never accepted a TCP connection within the
            startup timeout (E2E_SERVER_START_TIMEOUT in mcp-e2e.spec.md). This is a coarse
            "is anything listening" check, not a full MCP handshake, so this fixture stays
            agnostic of BEH-7's own scenario (a dead API_BASE_URL) — mcp-server itself must
            still start up cleanly even when its upstream is unreachable; only its tool calls
            fail in that case.
    """
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = {**os.environ, "PORT": str(port), "API_BASE_URL": api_base_url}
    proc = subprocess.Popen(
        [sys.executable, "-m", "mcp_server.server"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + _STARTUP_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                last_output = proc.stdout.read() if proc.stdout else ""
                raise E2EServerStartTimeout(
                    f"mcp-server process exited early (code {proc.returncode}) before "
                    f"accepting connections on {base_url} within the "
                    f"{_STARTUP_TIMEOUT_SECONDS}s startup timeout. Last output:\n{last_output}"
                )
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=1):
                    break
            except OSError:
                pass
            time.sleep(_POLL_INTERVAL_SECONDS)
        else:
            proc.kill()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            last_output = proc.stdout.read() if proc.stdout else ""
            raise E2EServerStartTimeout(
                f"mcp-server did not accept connections on {base_url} within the "
                f"{_STARTUP_TIMEOUT_SECONDS}s startup timeout. Last output:\n{last_output}"
            )
        yield base_url
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
