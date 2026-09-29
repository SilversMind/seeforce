"""A share link must show the same diagram as the owner sees, minus the ability
to change it. These tests pin the three ways it silently degraded instead."""
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.graph.models import ProjectMap, ShareToken, LexiconEntry, NodeOverlay

User = get_user_model()

_WORKSPACE = {
    "name": "Demo",
    "model": {
        "people": [],
        "softwareSystems": [
            {
                "id": "demo",
                "name": "Demo",
                "description": "",
                "tags": "Element,Software System",
                "relationships": [],
                "containers": [
                    {
                        "id": "demo-api",
                        "name": "API",
                        "technology": "Python",
                        "description": "",
                        "tags": "Element,Container",
                        "relationships": [],
                        "components": [],
                    }
                ],
            }
        ],
    },
    "views": {"systemContextViews": [], "containerViews": [], "componentViews": [],
              "configuration": {"styles": {"elements": [], "relationships": []}}},
}


class ShareReadParityTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", password="pass")
        self.pm = ProjectMap.objects.create(name="Demo", source_json=_WORKSPACE, owner=self.owner)
        self.token = ShareToken.objects.create(project_map=self.pm).token
        LexiconEntry.objects.create(project_map=self.pm, term="C4", definition="Context, Container, Component, Code")
        NodeOverlay.objects.create(
            project_map=self.pm, node_type="container", system_name="Demo",
            container_name="", node_name="API", tags=["core"],
        )

    def test_visitor_gets_the_lexicon(self):
        """Without this the glossary vanishes for the one person who needs it most."""
        res = self.client.get(f"/api/share/{self.token}/lexicon/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual([e["term"] for e in res.json()], ["C4"])

    def test_visitor_gets_the_tags(self):
        res = self.client.get(f"/api/share/{self.token}/tags/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["tags"], ["core"])

    def test_shared_view_carries_overlay_tags(self):
        """share_view used to build node overlays without the tags key, so a
        visitor's nodes came back untagged and the filter panel never appeared."""
        res = self.client.get(f"/api/share/{self.token}/view/C2/?system=demo")
        self.assertEqual(res.status_code, 200)
        api = next(n for n in res.json()["nodes"] if n["data"]["label"] == "API")
        self.assertEqual(api["data"]["tags"], ["core"])

    def test_owner_and_visitor_see_the_same_tags(self):
        self.client.force_login(self.owner)
        owner_tags = self.client.get(f"/api/graph/{self.pm.id}/tags/").json()["tags"]
        self.client.logout()
        visitor_tags = self.client.get(f"/api/share/{self.token}/tags/").json()["tags"]
        self.assertEqual(owner_tags, visitor_tags)

    def test_revoked_link_returns_404(self):
        ShareToken.objects.filter(project_map=self.pm).delete()
        for path in (f"/api/share/{self.token}/lexicon/", f"/api/share/{self.token}/tags/"):
            self.assertEqual(self.client.get(path).status_code, 404, path)
