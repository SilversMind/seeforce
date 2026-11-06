from unittest.mock import MagicMock, patch

from apps.graph.models import ProjectMap
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()

PULL = {
    "number": 42, "title": "Split the lexicon out",
    "head": {"ref": "feat/lexicon", "sha": "head1"},
    "base": {"ref": "main", "sha": "base1"},
}


def _ws(components):
    return {
        "name": "Shop",
        "model": {"people": [], "softwareSystems": [{
            "id": "shop", "name": "Shop", "description": "", "tags": "Element,Software System",
            "relationships": [], "containers": [{
                "id": "shop-api", "name": "API", "technology": "Django", "description": "",
                "tags": "Element,Container", "relationships": [], "components": components,
            }],
        }]},
    }


def _component(name, cid):
    return {"id": cid, "name": name, "technology": "Python", "description": "",
            "tags": "Element,Component", "source_file": f"{cid}.py", "relationships": []}


BASE_WS = _ws([_component("Order", "shop-api-order")])
HEAD_WS = _ws([_component("Order", "shop-api-order"), _component("Audit", "shop-api-audit")])


def _resp(status_code=200, payload=None):
    mock = MagicMock()
    mock.ok = 200 <= status_code < 300
    mock.status_code = status_code
    mock.json.return_value = payload
    return mock


class DeltaViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="reviewer", password="pass")
        self.pm = ProjectMap.objects.create(
            name="Shop", source_json=HEAD_WS, owner=self.user, github_repo="acme/shop",
            github_branch="main",
        )
        self.client.force_login(self.user)

    def _patch(self, pulls, *baselines):
        """Patch the token mint and both bound copies of the GitHub transport.

        NOTE: the pulls call goes through the name delta.py bound at import; the baseline reads go through github_import's own module global.
        """
        token = patch("apps.graph.views.delta._github_token", return_value="tok")
        listing = patch("apps.graph.views.delta._get_contents", return_value=pulls)
        reads = patch("apps.graph.views.github_import._get_contents", side_effect=list(baselines) or None)
        return token, listing, reads

    def test_open_pull_requests_are_listed_with_both_commits(self):
        token, listing, reads = self._patch(_resp(200, [PULL]))
        with token, listing, reads:
            res = self.client.get(f"/api/graph/{self.pm.id}/pulls/")
        assert res.status_code == 200
        assert res.json() == [{
            "number": 42, "title": "Split the lexicon out", "head_ref": "feat/lexicon",
            "base_ref": "main", "head_sha": "head1", "base_sha": "base1",
        }]

    def test_no_open_pull_request_is_an_empty_list_not_an_error(self):
        token, listing, reads = self._patch(_resp(200, []))
        with token, listing, reads:
            res = self.client.get(f"/api/graph/{self.pm.id}/pulls/")
        assert res.status_code == 200
        assert res.json() == []

    def test_a_requester_without_repository_access_is_refused(self):
        token, listing, reads = self._patch(_resp(403), _resp(403))
        with token, listing, reads:
            res = self.client.get(f"/api/graph/{self.pm.id}/pulls/")
        assert res.status_code == 403
        assert "access" in res.json()["error"]

    def test_an_anonymous_visitor_gets_no_comparison(self):
        self.client.logout()
        for url in (f"/api/graph/{self.pm.id}/pulls/",
                    f"/api/graph/{self.pm.id}/delta/view/C2/?pr=42"):
            assert self.client.get(url).status_code == 401

    def test_a_project_with_no_repository_link_says_so(self):
        self.pm.github_repo = ""
        self.pm.save(update_fields=["github_repo"])
        res = self.client.get(f"/api/graph/{self.pm.id}/pulls/")
        assert res.status_code == 400
        assert "not linked" in res.json()["error"]

    def test_the_delta_view_returns_the_decorated_head_map(self):
        token, listing, reads = self._patch(_resp(200, [PULL]), _resp(200, BASE_WS), _resp(200, HEAD_WS))
        with token, listing, reads:
            res = self.client.get(f"/api/graph/{self.pm.id}/delta/view/C3/?pr=42&container=shop-api")
        assert res.status_code == 200
        body = res.json()
        assert body["comparison"]["base_sha"] == "base1"
        assert body["summary"]["added"] == 1
        states = {n["id"]: n["data"]["delta"]["state"] for n in body["nodes"]}
        assert states == {"shop-api-order": "unchanged", "shop-api-audit": "added"}

    def test_a_missing_pr_number_is_refused(self):
        res = self.client.get(f"/api/graph/{self.pm.id}/delta/view/C2/")
        assert res.status_code == 400
        assert "pr=" in res.json()["error"]

    def test_a_pull_request_that_is_no_longer_open_cannot_be_compared(self):
        token, listing, reads = self._patch(_resp(200, []))
        with token, listing, reads:
            res = self.client.get(f"/api/graph/{self.pm.id}/delta/view/C2/?pr=42")
        assert res.status_code == 409
        assert res.json()["missing"] is None

    def test_a_baseline_missing_on_one_side_names_that_side(self):
        token, listing, reads = self._patch(_resp(200, [PULL]), _resp(404), _resp(404))
        with token, listing, reads:
            res = self.client.get(f"/api/graph/{self.pm.id}/delta/view/C2/?pr=42")
        assert res.status_code == 409
        assert res.json()["missing"] == "base"
        assert "workspace.json" in res.json()["error"]
