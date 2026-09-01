from seeforce_cli.mcp_static_facts import collapse_to_components


class _FakeImport:
    def __init__(self, raw, resolved_path):
        self.raw = raw
        self.resolved_path = resolved_path


class _FakeFileFacts:
    def __init__(self, file, imports):
        self.file = file
        self.imports = imports
        self.defines = []


def _owner(name):
    return {"confidence": "exact", "kind": "component", "element": {"name": name}, "candidates": []}


_UNKNOWN = {"confidence": "unknown", "kind": None, "element": None, "candidates": []}


def test_collapse_keeps_cross_component_edge():
    facts = [_FakeFileFacts("a.py", [_FakeImport("pkg.b", "b.py")])]

    def infer_owner(file_path, ws):
        return _owner("ComponentA") if file_path == "a.py" else _owner("ComponentB")

    edges = collapse_to_components(facts, {}, infer_owner)
    assert len(edges) == 1
    assert edges[0]["from_component"] == "ComponentA"
    assert edges[0]["to_component"] == "ComponentB"


def test_collapse_drops_intra_component_edge():
    facts = [_FakeFileFacts("a.py", [_FakeImport("pkg.b", "b.py")])]

    def infer_owner(file_path, ws):
        return _owner("SameComponent")

    edges = collapse_to_components(facts, {}, infer_owner)
    assert edges == []


def test_collapse_keeps_unknown_owner_on_cold_start():
    facts = [_FakeFileFacts("a.py", [_FakeImport("pkg.b", "b.py")])]

    def infer_owner(file_path, ws):
        return _UNKNOWN

    edges = collapse_to_components(facts, {}, infer_owner)
    assert len(edges) == 1
    assert edges[0]["from_component"] is None
    assert edges[0]["to_component"] is None


def test_collapse_external_known_import_has_no_to_component():
    facts = [_FakeFileFacts("a.py", [_FakeImport("stripe", None)])]

    def infer_owner(file_path, ws):
        return _owner("ComponentA")

    edges = collapse_to_components(facts, {}, infer_owner)
    assert len(edges) == 1
    assert edges[0]["to_file"] is None
    assert edges[0]["to_component"] is None
