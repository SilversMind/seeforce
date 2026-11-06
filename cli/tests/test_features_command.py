import json
from pathlib import Path

from click.testing import CliRunner
from seeforce_cli.main import cli


def _ws(*components):
    return {
        "name": "T",
        "model": {
            "softwareSystems": [
                {
                    "id": "seeforce",
                    "name": "SeeForce",
                    "containers": [
                        {
                            "id": "seeforce-cli",
                            "name": "SeeForce CLI",
                            "components": [
                                {"id": f"seeforce-cli-{c.lower()}", "name": c} for c in components
                            ],
                        }
                    ],
                }
            ]
        },
    }


def _catalogue(*features):
    return {
        "version": 1,
        "generated_at": "2026-11-06T00:00:00Z",
        "categories": [{"name": "Projects", "features": list(features)}],
    }


def _feature(**over):
    f = {
        "id": "import-a-project",
        "name": "Import a project",
        "intent": "Turn a repo into a map.",
        "kind": "capability",
        "components": ["Importer (SeeForce CLI)"],
        "reviewed_at": None,
        "entry_points": ["cli:import"],
        "paths": [],
    }
    f.update(over)
    return f


def _repo(tmp_path: Path, workspace=None, catalogue=None) -> Path:
    seeforce = tmp_path / ".seeforce"
    seeforce.mkdir()
    if workspace is not None:
        (seeforce / "workspace.json").write_text(json.dumps(workspace))
    if catalogue is not None:
        (seeforce / "features.json").write_text(json.dumps(catalogue))
    return tmp_path


def _run(root, *args):
    return CliRunner().invoke(cli, ["features", "--path", str(root), *args])


def test_a_valid_catalogue_exits_zero_and_lists_the_features(tmp_path):
    root = _repo(tmp_path, _ws("Importer"), _catalogue(_feature()))
    result = _run(root)
    assert result.exit_code == 0, result.output
    assert "Import a project" in result.output
    assert "generated" in result.output


def test_capabilities_and_prerequisites_are_listed_apart(tmp_path):
    root = _repo(
        tmp_path,
        _ws("Importer", "Auth"),
        _catalogue(
            _feature(),
            _feature(id="sign-in", name="Sign in", kind="prerequisite",
                     components=["Auth (SeeForce CLI)"]),
        ),
    )
    result = _run(root)
    assert result.exit_code == 0, result.output
    assert result.output.index("Capabilities") < result.output.index("Prerequisites")


def test_a_reviewed_feature_is_marked_reviewed(tmp_path):
    root = _repo(tmp_path, _ws("Importer"), _catalogue(_feature(reviewed_at="a" * 40)))
    result = _run(root)
    assert "[reviewed]" in result.output


def test_a_failed_validation_rule_exits_two(tmp_path):
    root = _repo(tmp_path, _ws("Importer"), _catalogue(_feature(components=["Ghost (SeeForce CLI)"])))
    result = _run(root)
    assert result.exit_code == 2, result.output
    assert "Ghost (SeeForce CLI)" in result.output


def test_an_unknown_version_exits_two(tmp_path):
    catalogue = _catalogue(_feature())
    catalogue["version"] = 99
    root = _repo(tmp_path, _ws("Importer"), catalogue)
    result = _run(root)
    assert result.exit_code == 2, result.output
    assert "version" in result.output


def test_no_catalogue_exits_zero_with_an_explanation(tmp_path):
    root = _repo(tmp_path, _ws("Importer"))
    result = _run(root)
    assert result.exit_code == 0, result.output
    assert "No catalogue" in result.output
    assert "catalogue_features" in result.output


def test_no_model_exits_two_naming_the_prerequisite(tmp_path):
    root = _repo(tmp_path, catalogue=_catalogue(_feature()))
    result = _run(root)
    assert result.exit_code == 2, result.output
    assert "seeforce scan ." in result.output


def test_review_flags_are_reported_without_failing(tmp_path):
    root = _repo(
        tmp_path,
        _ws("Importer"),
        _catalogue(_feature(name="Import and share", entry_points=[])),
    )
    result = _run(root)
    assert result.exit_code == 0, result.output
    assert "conjunction" in result.output
    assert "claims no entry point" in result.output


def test_json_prints_the_parsed_catalogue(tmp_path):
    root = _repo(tmp_path, _ws("Importer"), _catalogue(_feature()))
    result = _run(root, "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["categories"][0]["features"][0]["id"] == "import-a-project"


def test_malformed_json_exits_two(tmp_path):
    root = _repo(tmp_path, _ws("Importer"))
    (root / ".seeforce" / "features.json").write_text("{not json")
    result = _run(root)
    assert result.exit_code == 2, result.output
    assert "not valid JSON" in result.output
