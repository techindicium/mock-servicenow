import subprocess
import sys


def test_bare_pytest_collection_excludes_tests_e2e():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--collect-only"],
        capture_output=True, text=True, cwd=".",
    )
    # Checked with a trailing "/" (a real collected node id from that directory would
    # read "tests_e2e/test_....py::..."), not the bare substring "tests_e2e" — this
    # test's own node id (tests/test_pytest_config.py::..._excludes_tests_e2e) contains
    # that bare substring in its own name and would otherwise always self-match.
    assert "tests_e2e/" not in result.stdout
