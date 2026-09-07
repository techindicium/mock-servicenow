from pathlib import Path

import yaml


def test_e2e_smoke_gate_is_defined_correctly():
    doc = yaml.safe_load(Path(".context-index/governance/gates.yaml").read_text())
    gates = {g["id"]: g for g in doc["gates"]}
    assert "e2e-smoke" in gates
    gate = gates["e2e-smoke"]
    assert gate["tier"] == "e2e"
    assert gate["command"] == ["python3", "-m", "pytest", "-q", "tests_e2e/"]
    assert gate.get("required") is False or gate.get("severity") == "warning"
