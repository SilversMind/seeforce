

def test_install_sh_served(client):
    r = client.get("/install.sh")
    assert r.status_code == 200
    assert b"uv tool install" in r.content
    assert r["Content-Type"].startswith("text/plain")


def test_install_sh_contains_seeforce_repo(client):
    r = client.get("/install.sh")
    assert b"SilversMind/seeforce" in r.content
