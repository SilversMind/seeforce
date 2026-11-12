"""A component reaching into another container must surface as a C2 relationship."""
from c4parser.builder import build
from c4parser.scanner import scan

SYSTEM = '"""\n@c1:system\nname: S\ndescription: A system.\n"""\n'
FRONT = '"""\n@c2:container\nname: Front\nsystem: S\ndescription: The front.\n"""\n'
BACK = '"""\n@c2:container\nname: Back\nsystem: S\ndescription: The back.\n"""\n'
CALLER = (
    '"""\n@c3:component\nname: Caller\ncontainer: Front\ndescription: Calls across.\n'
    'uses:\n- Back/Callee: "asks for the thing"\n"""\n'
)
CALLEE = '"""\n@c3:component\nname: Callee\ncontainer: Back\ndescription: Answers.\n"""\n'


def _edges(workspace, container_name):
    index = {}
    for system in workspace["model"]["softwareSystems"]:
        for container in system.get("containers", []):
            index[container["id"]] = container["name"]
    for system in workspace["model"]["softwareSystems"]:
        for container in system.get("containers", []):
            if container["name"] == container_name:
                return [
                    (index.get(r["destinationId"]), r["description"])
                    for r in container["relationships"]
                ]
    return []


def _write(root, authored_container_edge=False):
    (root / "sys.py").write_text(SYSTEM)
    front = FRONT
    if authored_container_edge:
        front = front[:-4] + 'uses:\n- Back: "the authored one"\n"""\n'
    (root / "front.py").write_text(front)
    (root / "back.py").write_text(BACK)
    (root / "caller.py").write_text(CALLER)
    (root / "callee.py").write_text(CALLEE)


def test_a_component_crossing_a_container_surfaces_as_a_c2_edge(tmp_path):
    _write(tmp_path)
    edges = _edges(build(scan(str(tmp_path))), "Front")
    assert ("Back", "asks for the thing") in edges


def test_an_authored_container_edge_is_not_duplicated_by_the_rollup(tmp_path):
    _write(tmp_path, authored_container_edge=True)
    edges = _edges(build(scan(str(tmp_path))), "Front")
    assert [d for d, _ in edges].count("Back") == 1
    assert ("Back", "the authored one") in edges
