import json

import pytest
from c4parser.exceptions import C4ValidationError
from c4parser.features import (
    dump_catalogue,
    load_catalogue,
    review_flags,
)


def _slug(*parts):
    return "-".join(p.lower().replace(" ", "-") for p in parts)


def ws(*components, system="SeeForce", container="SeeForce CLI"):
    return {
        "model": {
            "people": [],
            "softwareSystems": [
                {
                    "name": system,
                    "id": _slug(system),
                    "containers": [
                        {
                            "name": container,
                            "id": _slug(system, container),
                            "components": [
                                {"name": c, "id": _slug(system, container, c)} for c in components
                            ],
                        }
                    ],
                }
            ],
        }
    }


def catalogue(**feature):
    f = {
        "id": "import-a-project",
        "name": "Import a project",
        "intent": "Turn a GitHub repo into a map.",
        "kind": "capability",
        "components": ["Importer (SeeForce CLI)"],
        "reviewed_at": None,
        "entry_points": ["cli:import"],
        "paths": [],
    }
    f.update(feature)
    return {
        "version": 1,
        "generated_at": "2026-11-06T00:00:00Z",
        "categories": [{"name": "Projects", "features": [f]}],
    }


MODEL = ws("Importer")


def test_valid_catalogue_round_trips():
    cat = load_catalogue(catalogue(), MODEL)
    assert cat.version == 1
    assert [c.name for c in cat.categories] == ["Projects"]
    feature = cat.categories[0].features[0]
    assert feature.kind == "capability"
    assert feature.reviewed_at is None
    assert json.loads(dump_catalogue(cat)) == catalogue()


def test_unknown_version_raises():
    for bad in ({**catalogue(), "version": 2}, {k: v for k, v in catalogue().items() if k != "version"}):
        with pytest.raises(C4ValidationError, match="version"):
            load_catalogue(bad, MODEL)


def test_unresolvable_component_raises_naming_it():
    bad = catalogue(components=["Ghost (SeeForce CLI)"])
    with pytest.raises(C4ValidationError, match=r"Ghost \(SeeForce CLI\)"):
        load_catalogue(bad, MODEL)


def test_duplicate_feature_id_raises():
    cat = catalogue()
    cat["categories"][0]["features"].append(dict(cat["categories"][0]["features"][0]))
    with pytest.raises(C4ValidationError, match="import-a-project"):
        load_catalogue(cat, MODEL)


def test_duplicate_category_name_raises():
    cat = catalogue()
    cat["categories"].append({"name": "Projects", "features": []})
    with pytest.raises(C4ValidationError, match="Projects"):
        load_catalogue(cat, MODEL)


def test_empty_components_raises():
    with pytest.raises(C4ValidationError, match="components"):
        load_catalogue(catalogue(components=[]), MODEL)


def test_missing_required_field_raises():
    cat = catalogue()
    del cat["categories"][0]["features"][0]["intent"]
    with pytest.raises(C4ValidationError, match="intent"):
        load_catalogue(cat, MODEL)


def test_single_component_feature_is_valid():
    cat = load_catalogue(catalogue(components=["Importer (SeeForce CLI)"]), MODEL)
    assert cat.categories[0].features[0].components == ["Importer (SeeForce CLI)"]


def test_path_collision_fails_naming_both_elements():
    """Two systems holding same-named containers collide on one key — FR-033a, the SC-008 false negative."""
    model = ws("Importer")
    model["model"]["softwareSystems"].append(
        ws("Importer", system="Other")["model"]["softwareSystems"][0]
    )
    with pytest.raises(C4ValidationError) as exc:
        load_catalogue(catalogue(), model)
    message = str(exc.value)
    assert "Importer (SeeForce CLI)" in message
    assert "seeforce-seeforce-cli-importer" in message
    assert "other-seeforce-cli-importer" in message


def test_review_flags_fire_without_raising():
    cat = load_catalogue(
        catalogue(name="Import and share", entry_points=[]),
        MODEL,
    )
    flags = review_flags(cat, entry_points=[])
    assert any("conjunction" in f for f in flags)
    assert any("entry point" in f for f in flags)


def test_feature_name_equal_to_category_name_is_flagged():
    cat = load_catalogue(catalogue(name="Projects"), MODEL)
    assert any("category" in f for f in review_flags(cat, entry_points=["cli:import"]))


def test_claimed_entry_point_discovery_no_longer_finds_is_flagged():
    cat = load_catalogue(catalogue(), MODEL)
    assert any("cli:import" in f for f in review_flags(cat, entry_points=["cli:other"]))


def test_reviewed_feature_keeps_its_commit():
    cat = load_catalogue(catalogue(reviewed_at="a" * 40), MODEL)
    assert cat.categories[0].features[0].reviewed_at == "a" * 40
