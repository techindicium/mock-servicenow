from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_requirements_e2e_includes_mcp_sdk_via_requirements():
    content = (REPO_ROOT / "requirements-e2e.txt").read_text()
    assert "-r requirements.txt" in content, (
        "mcp e2e tests need the mcp SDK/httpx pinned in requirements.txt (the single canonical "
        "dependency file owned by incident-tools.plan.md Task 1); include it rather than "
        "re-pinning separately"
    )
