import json
from pathlib import Path

from c4parser import build, export_workspace, scan

FIXTURES = Path(__file__).parent / "fixtures" / "sample_project"


def test_export_produces_valid_json():
    elements = scan(str(FIXTURES))
    workspace = build(elements)
    result = export_workspace(workspace)
    parsed = json.loads(result)
    assert "model" in parsed
    assert "views" in parsed


def test_export_round_trip():
    elements = scan(str(FIXTURES))
    workspace = build(elements)
    result = export_workspace(workspace)
    parsed = json.loads(result)
    systems = parsed["model"]["softwareSystems"]
    assert any(s["name"] == "Shop" for s in systems)
