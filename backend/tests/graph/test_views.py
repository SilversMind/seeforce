import json
from django.test import TestCase
from django.urls import reverse
from apps.graph.models import ProjectMap


SAMPLE_WORKSPACE = {
    "name": "Test ProjectMap",
    "model": {"people": [], "softwareSystems": []},
    "views": {
        "systemContextViews": [],
        "containerViews": [],
        "componentViews": [],
        "configuration": {"styles": {"elements": [], "relationships": []}},
    },
}


class UploadProjectMapTest(TestCase):
    def test_upload_creates_workspace(self):
        response = self.client.post(
            "/api/graph/upload/",
            data=json.dumps({"name": "My Project", "workspace": SAMPLE_WORKSPACE}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], "My Project")
        self.assertEqual(ProjectMap.objects.count(), 1)

    def test_upload_missing_workspace_returns_400(self):
        response = self.client.post(
            "/api/graph/upload/",
            data=json.dumps({"name": "Bad"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_non_dict_workspace_returns_400(self):
        for payload in ([1, 2, 3], 42, "workspace"):
            response = self.client.post(
                "/api/graph/upload/",
                data=json.dumps({"name": "Bad", "workspace": payload}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("workspace", response.json())


class FetchProjectMapTest(TestCase):
    def setUp(self):
        self.ws = ProjectMap.objects.create(name="Test", source_json=SAMPLE_WORKSPACE)

    def test_fetch_returns_workspace(self):
        response = self.client.get(f"/api/graph/{self.ws.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test")
        self.assertIn("source_json", data)

    def test_fetch_unknown_returns_404(self):
        response = self.client.get("/api/graph/99999/")
        self.assertEqual(response.status_code, 404)


class ListProjectMapsTest(TestCase):
    def setUp(self):
        ProjectMap.objects.create(name="Alpha", source_json={})
        ProjectMap.objects.create(name="Beta", source_json={})

    def test_list_returns_all_projects(self):
        response = self.client.get("/api/graph/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        names = {p["name"] for p in data}
        self.assertIn("Alpha", names)
        self.assertIn("Beta", names)

    def test_list_contains_required_fields(self):
        response = self.client.get("/api/graph/")
        self.assertEqual(response.status_code, 200)
        item = response.json()[0]
        for field in ("id", "name", "project_id", "updated_at"):
            self.assertIn(field, item)

    def test_list_ordered_by_updated_at_desc(self):
        response = self.client.get("/api/graph/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data[0]["name"], "Beta")  # created last = updated_at newest
