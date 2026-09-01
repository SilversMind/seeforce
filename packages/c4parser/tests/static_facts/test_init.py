import c4parser.static_facts as sf


def test_extract_facts_degrades_without_backend(monkeypatch):
    monkeypatch.setattr(sf, "_backend_available", lambda: False)
    assert sf.extract_facts(".", ["whatever.py"]) == []


def test_extract_facts_empty_file_list():
    assert sf.extract_facts(".", []) == []
