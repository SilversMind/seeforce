"""A scan must not depend on the order the filesystem hands back directory entries."""
import json

from c4parser.builder import build
from c4parser.scanner import scan

SYSTEM = '"""\n@c1:system\nname: S\ndescription: A system.\n"""\n'
CONTAINER = '"""\n@c2:container\nname: C\nsystem: S\ndescription: A container.\n"""\n'
COMPONENT = '"""\n@c3:component\nname: {name}\ncontainer: C\ndescription: A component.\n"""\n'


def _tree(root):
    (root / "sys.py").write_text(SYSTEM)
    (root / "cont.py").write_text(CONTAINER)
    for sub, names in (("a", ("Alpha", "Beta")), ("b", ("Gamma", "Delta"))):
        d = root / sub
        d.mkdir()
        for n in names:
            (d / f"{n.lower()}.py").write_text(COMPONENT.format(name=n))


def test_scan_is_stable_under_reversed_walk(tmp_path, monkeypatch):
    _tree(tmp_path)
    first = json.dumps(build(scan(str(tmp_path))), indent=2)

    import os

    real_walk = os.walk

    def reversed_walk(top, *a, **kw):
        for dirpath, dirnames, filenames in real_walk(top, *a, **kw):
            dirnames.sort(reverse=True)
            yield dirpath, dirnames, sorted(filenames, reverse=True)

    monkeypatch.setattr(os, "walk", reversed_walk)
    assert json.dumps(build(scan(str(tmp_path))), indent=2) == first


if __name__ == "__main__":
    import pathlib
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        _tree(root)
        print(json.dumps(build(scan(str(root))), indent=2)[:200])
