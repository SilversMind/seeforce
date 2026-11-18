"""Each container and component is weighed by the lines of code of the files it owns."""
import subprocess

from c4parser.builder import build
from c4parser.scanner import count_lines, scan

SYSTEM = '"""\n@c1:system\nname: S\nshort_desc: s\ndescription: |\n  - a system\n"""\n'
CONTAINER = '"""\n@c2:container\nname: C\nsystem: S\nshort_desc: c\ndescription: |\n  - a container\n"""\n'
COMPONENT = '"""\n@c3:component\nname: {name}\ncontainer: C\nshort_desc: x\ndescription: |\n  - a component\n"""\n'


def _code(lines: int) -> str:
    return "\n".join(f"x{i} = {i}" for i in range(lines)) + "\n\n\n"


def _components(workspace: dict) -> dict[str, int]:
    cont = workspace["model"]["softwareSystems"][0]["containers"][0]
    return {c["name"]: c["loc"] for c in cont["components"]}


def _workspace(tmp_path) -> dict:
    # source_file is relative to the git root, so the folders only count inside a repo.
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "sys.py").write_text(SYSTEM)
    (tmp_path / "cont.py").write_text(CONTAINER + _code(10))
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "alpha.py").write_text(COMPONENT.format(name="Alpha") + _code(20))
    (tmp_path / "a" / "helper.py").write_text(_code(30))
    (tmp_path / "a" / "deep").mkdir()
    (tmp_path / "a" / "deep" / "more.py").write_text(_code(40))
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "shared.py").write_text(COMPONENT.format(name="Beta") + COMPONENT.format(name="Gamma") + _code(50))
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "util.py").write_text(_code(60))
    return build(scan(str(tmp_path)), line_counts=count_lines(str(tmp_path)))


def test_count_lines_skips_blank_lines(tmp_path):
    (tmp_path / "f.py").write_text("a = 1\n\n   \nb = 2\n")
    assert count_lines(str(tmp_path)) == {"f.py": 2}


def test_unannotated_files_go_to_the_nearest_component(tmp_path):
    sizes = _components(_workspace(tmp_path))
    annotation = len(COMPONENT.format(name="Alpha").splitlines())
    assert sizes["Alpha"] == annotation + 20 + 30 + 40


def test_components_sharing_a_file_split_its_lines(tmp_path):
    sizes = _components(_workspace(tmp_path))
    assert sizes["Beta"] == sizes["Gamma"] > 0


def test_container_weighs_its_files_and_its_components(tmp_path):
    workspace = _workspace(tmp_path)
    system = workspace["model"]["softwareSystems"][0]
    cont = system["containers"][0]
    own = len(CONTAINER.splitlines()) + 10 + len(SYSTEM.splitlines()) + 60
    assert cont["loc"] == own + sum(_components(workspace).values())
    assert system["loc"] == cont["loc"]


def test_no_line_counts_leaves_the_workspace_unchanged(tmp_path):
    (tmp_path / "sys.py").write_text(SYSTEM)
    (tmp_path / "cont.py").write_text(CONTAINER + COMPONENT.format(name="Alpha"))
    workspace = build(scan(str(tmp_path)))
    assert "loc" not in workspace["model"]["softwareSystems"][0]["containers"][0]
