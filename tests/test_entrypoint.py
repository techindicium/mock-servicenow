"""Exercises docker/itsm-api/entrypoint.sh as a real shell script (stubbing python3/uvicorn on
PATH), rather than only testing the Python side of the exit-code contract it depends on --
this is the actual mechanism that recovers from a database an interrupted prior seed run left
partially seeded (see app/seed.py's main() and entrypoint.sh's own comment)."""
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENTRYPOINT = REPO_ROOT / "docker" / "itsm-api" / "entrypoint.sh"

_STUB_PYTHON3 = """#!/bin/sh
# Simulates app.seed: exits 2 (SEED_STATE_INCONSISTENT) on its first call, leaving a marker
# file where the real database would be; exits 0 on any later call, but only if that marker
# is gone -- i.e. only if entrypoint.sh actually wiped it before retrying.
count_file="$STUB_STATE_DIR/count"
count=0
[ -f "$count_file" ] && count=$(cat "$count_file")
count=$((count + 1))
echo "$count" > "$count_file"

if [ "$count" -eq 1 ]; then
  : > "$DATABASE_PATH"
  exit 2
fi

if [ -f "$DATABASE_PATH" ]; then
  echo "db file still present on retry -- entrypoint.sh did not wipe it" >&2
  exit 9
fi
exit 0
"""

_STUB_UVICORN = """#!/bin/sh
echo "uvicorn started: $*"
"""


def _write_stub(path, content):
    path.write_text(content)
    path.chmod(0o755)


def test_entrypoint_wipes_and_retries_once_on_exit_code_2(tmp_path):
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_stub(stub_bin / "python3", _STUB_PYTHON3)
    _write_stub(stub_bin / "uvicorn", _STUB_UVICORN)

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    db_path = tmp_path / "mock_servicenow.db"

    env = dict(os.environ)
    env["PATH"] = f"{stub_bin}:{env['PATH']}"
    env["STUB_STATE_DIR"] = str(state_dir)
    env["DATABASE_PATH"] = str(db_path)
    env["PORT"] = "8030"

    result = subprocess.run(
        ["/bin/sh", str(ENTRYPOINT)], env=env, capture_output=True, text=True, timeout=10
    )

    assert result.returncode == 0, result.stderr
    assert (state_dir / "count").read_text().strip() == "2"
    assert "uvicorn started:" in result.stdout
    assert not db_path.exists()  # wiped before the retry, and the stub never recreates it


def test_entrypoint_does_not_retry_on_other_exit_codes(tmp_path):
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_stub(
        stub_bin / "python3",
        "#!/bin/sh\necho '1' > \"$STUB_STATE_DIR/count\"\nexit 1\n",
    )
    _write_stub(stub_bin / "uvicorn", _STUB_UVICORN)

    state_dir = tmp_path / "state"
    state_dir.mkdir()

    env = dict(os.environ)
    env["PATH"] = f"{stub_bin}:{env['PATH']}"
    env["STUB_STATE_DIR"] = str(state_dir)
    env["DATABASE_PATH"] = str(tmp_path / "mock_servicenow.db")
    env["PORT"] = "8030"

    result = subprocess.run(
        ["/bin/sh", str(ENTRYPOINT)], env=env, capture_output=True, text=True, timeout=10
    )

    assert result.returncode == 1
    assert "uvicorn started:" not in result.stdout
