import json
import pytest
from django.test import TestCase
from django.urls import reverse
from apps.graph.models import Workspace


SAMPLE_WORKSPACE = {
    "name": "Test Workspace",
    "model": {"people": [], "softwareSystems": []},
    "views": {
        "systemContextViews": [],
        "containerViews": [],
        "componentViews": [],
        "configuration": {"styles": {"elements": [], "relationships": []}},
    },
}


class UploadWorkspaceTest(TestCase):
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
        self.assertEqual(Workspace.objects.count(), 1)

    def test_upload_missing_workspace_returns_400(self):
        response = self.client.post(
            "/api/graph/upload/",
            data=json.dumps({"name": "Bad"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class FetchWorkspaceTest(TestCase):
    def setUp(self):
        self.ws = Workspace.objects.create(name="Test", source_json=SAMPLE_WORKSPACE)

    def test_fetch_returns_workspace(self):
        response = self.client.get(f"/api/graph/{self.ws.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test")
        self.assertIn("source_json", data)

    def test_fetch_unknown_returns_404(self):
        response = self.client.get("/api/graph/99999/")
        self.assertEqual(response.status_code, 404)
