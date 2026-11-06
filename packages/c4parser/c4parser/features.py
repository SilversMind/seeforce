"""
@c3:component
name: Feature Catalogue
container: Annotation Parser
technology: Python
description: Loads, validates and serialises the feature catalogue — the list of intentions a repo serves, grouped into categories, each naming the set of model elements it touches. Resolves every element the catalogue names against a workspace snapshot flattened by Delta Reporter, so the catalogue stays a reading of the model and can assert no structure of its own. Refuses to load rather than degrade — an unknown schema version, an element that resolves to nothing, or two model elements colliding on one path all raise instead of yielding a partial catalogue. Also owns the append-only merge that keeps a human-reviewed feature byte-identical across regenerations.
short_desc: Loads and validates the feature catalogue against a workspace snapshot
"""
import json
from dataclasses import asdict, dataclass, field

from .delta import flatten
from .exceptions import C4ValidationError

VERSION = 1
KINDS = ("capability", "prerequisite")
REQUIRED_FEATURE_FIELDS = ("id", "name", "intent", "kind", "components")
# A name joining two intentions is a bag, not a feature — FR-006.
CONJUNCTIONS = (" and ", " or ", " & ", " + ", ",", "/")


@dataclass
class Feature:
    """One intention the repo serves, naming the model elements it touches."""
    id: str
    name: str
    intent: str
    kind: str
    components: list[str]
    reviewed_at: str | None = None
    entry_points: list[str] = field(default_factory=list)
    paths: list[dict] = field(default_factory=list)

    @property
    def reviewed(self) -> bool:
        return bool(self.reviewed_at)


@dataclass
class Category:
    """A free-text grouping carrying a name only."""
    name: str
    features: list[Feature] = field(default_factory=list)


@dataclass
class Catalogue:
    version: int
    generated_at: str
    categories: list[Category] = field(default_factory=list)

    def features(self) -> list[Feature]:
        return [f for c in self.categories for f in c.features]


def element_index(workspace: dict) -> dict[str, str]:
    """Map every element path to its id, reusing the comparison's own vocabulary (FR-033)."""
    index: dict[str, str] = {}
    for element in flatten(workspace):
        if element.path in index:
            # Not widened: a wider key would change an already-merged comparison's output,
            # NOTE: and silently intersecting on an ambiguous one is the false negative SC-008 forbids.
            raise C4ValidationError(
                f"two model elements share the path {element.path!r} "
                f"(ids {index[element.path]!r} and {element.id!r}) — "
                "the catalogue cannot tell them apart, so it refuses to load"
            )
        index[element.path] = element.id
    return index


def _require(raw: dict, keys: tuple[str, ...], what: str) -> None:
    missing = [k for k in keys if raw.get(k) is None]
    if missing:
        raise C4ValidationError(f"{what} is missing required field(s): {', '.join(missing)}")


def _feature(raw: dict, index: dict[str, str]) -> Feature:
    if not isinstance(raw, dict):
        raise C4ValidationError(f"a feature must be a JSON object, got {type(raw).__name__}")
    _require(raw, REQUIRED_FEATURE_FIELDS, f"feature {raw.get('id') or '<no id>'!r}")

    if raw["kind"] not in KINDS:
        raise C4ValidationError(
            f"feature {raw['id']!r} has kind {raw['kind']!r} — expected one of {', '.join(KINDS)}"
        )
    components = raw["components"]
    if not isinstance(components, list) or not components:
        raise C4ValidationError(
            f"feature {raw['id']!r} has an empty components list — a feature names at least one element"
        )
    unresolved = [c for c in components if c not in index]
    if unresolved:
        raise C4ValidationError(
            f"feature {raw['id']!r} names {', '.join(repr(c) for c in unresolved)}, "
            "which resolve(s) to no model element — regenerate the catalogue against the current model"
        )
    return Feature(
        id=raw["id"],
        name=raw["name"],
        intent=raw["intent"],
        kind=raw["kind"],
        components=list(components),
        reviewed_at=raw.get("reviewed_at"),
        entry_points=list(raw.get("entry_points") or []),
        paths=list(raw.get("paths") or []),
    )


def load_catalogue(raw: dict, workspace: dict) -> Catalogue:
    """Parse and fully validate a catalogue against a workspace, or raise. Never loads partially."""
    if not isinstance(raw, dict):
        raise C4ValidationError(f"catalogue must be a JSON object, got {type(raw).__name__}")
    if raw.get("version") != VERSION:
        raise C4ValidationError(
            f"catalogue version {raw.get('version')!r} is not supported (this reader knows {VERSION}) "
            "— refusing to guess at an unknown schema"
        )
    _require(raw, ("generated_at", "categories"), "catalogue")

    index = element_index(workspace)
    categories: list[Category] = []
    seen_categories: set[str] = set()
    seen_features: set[str] = set()

    for raw_category in raw["categories"]:
        name = (raw_category or {}).get("name")
        if not name:
            raise C4ValidationError("a category is missing required field(s): name")
        if name in seen_categories:
            raise C4ValidationError(f"category name {name!r} is duplicated")
        seen_categories.add(name)

        features = []
        for raw_feature in raw_category.get("features") or []:
            feature = _feature(raw_feature, index)
            if feature.id in seen_features:
                raise C4ValidationError(f"feature id {feature.id!r} is duplicated")
            seen_features.add(feature.id)
            features.append(feature)
        categories.append(Category(name=name, features=features))

    return Catalogue(version=raw["version"], generated_at=raw["generated_at"], categories=categories)


def dump_catalogue(catalogue: Catalogue) -> str:
    """Serialise a catalogue back to the on-disk JSON."""
    return json.dumps(asdict(catalogue), indent=2, ensure_ascii=False) + "\n"


def review_flags(catalogue: Catalogue, entry_points: list[str]) -> list[str]:
    """Advisory findings a human should look at. None of these blocks a load."""
    known = set(entry_points)
    flags: list[str] = []
    for category in catalogue.categories:
        for feature in category.features:
            lowered = f" {feature.name.lower()} "
            if any(c in lowered for c in CONJUNCTIONS):
                flags.append(
                    f"{feature.id}: name {feature.name!r} contains a conjunction — "
                    "two intentions in one feature?"
                )
            if feature.name == category.name:
                flags.append(
                    f"{feature.id}: name {feature.name!r} equals its category name — "
                    "the grouping probably found a bag, not a feature"
                )
            if not feature.entry_points:
                flags.append(f"{feature.id}: claims no entry point")
            else:
                gone = [e for e in feature.entry_points if e not in known]
                if gone:
                    flags.append(
                        f"{feature.id}: claims entry point(s) {', '.join(repr(e) for e in gone)} "
                        "that discovery no longer finds"
                    )
    return flags
