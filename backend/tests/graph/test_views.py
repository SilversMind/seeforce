import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.graph.models import ProjectMap

User = get_user_model()

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
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.client.force_login(self.user)

    def test_upload_creates_workspace(self):
        response = self.client.post(
            "/api/graph/",
            data=json.dumps({"name": "My Project", "workspace": SAMPLE_WORKSPACE}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], "My Project")
        self.assertEqual(ProjectMap.objects.count(), 1)

    def test_upload_assigns_uploader_as_owner(self):
        response = self.client.post(
            "/api/graph/",
            data=json.dumps({"name": "My Project", "workspace": SAMPLE_WORKSPACE}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        pm = ProjectMap.objects.first()
        self.assertEqual(pm.owner, self.user)

    def test_upload_unauthenticated_returns_401(self):
        self.client.logout()
        response = self.client.post(
            "/api/graph/",
            data=json.dumps({"name": "My Project", "workspace": SAMPLE_WORKSPACE}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_upload_missing_workspace_returns_400(self):
        response = self.client.post(
            "/api/graph/",
            data=json.dumps({"name": "Bad"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_upload_non_dict_workspace_returns_400(self):
        for payload in ([1, 2, 3], 42, "workspace"):
            response = self.client.post(
                "/api/graph/",
                data=json.dumps({"name": "Bad", "workspace": payload}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("workspace", response.json())


class FetchProjectMapTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.client.force_login(self.user)
        self.ws = ProjectMap.objects.create(name="Test", source_json=SAMPLE_WORKSPACE, owner=self.user)

    def test_fetch_returns_workspace(self):
        response = self.client.get(f"/api/graph/{self.ws.id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test")
        self.assertIn("source_json", data)

    def test_fetch_unknown_returns_404(self):
        response = self.client.get("/api/graph/99999/")
        self.assertEqual(response.status_code, 404)

    def test_fetch_unauthenticated_returns_401(self):
        self.client.logout()
        response = self.client.get(f"/api/graph/{self.ws.id}/")
        self.assertEqual(response.status_code, 401)

    def test_fetch_other_owners_project_returns_403(self):
        other_pm = ProjectMap.objects.create(name="Other", source_json={}, owner=self.other)
        res = self.client.get(f"/api/graph/{other_pm.id}/")
        self.assertEqual(res.status_code, 403)

    def test_fetch_unowned_project_returns_403(self):
        unowned = ProjectMap.objects.create(name="Unowned", source_json={})
        res = self.client.get(f"/api/graph/{unowned.id}/")
        self.assertEqual(res.status_code, 403)


class ListProjectMapsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.client.force_login(self.user)
        self.pm_mine = ProjectMap.objects.create(name="Alpha", source_json={}, owner=self.user)
        self.pm_theirs = ProjectMap.objects.create(name="Beta", source_json={}, owner=self.other)

    def test_list_returns_only_own_projects(self):
        response = self.client.get("/api/graph/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Alpha")

    def test_list_contains_required_fields(self):
        response = self.client.get("/api/graph/")
        self.assertEqual(response.status_code, 200)
        item = response.json()[0]
        for field in ("id", "name", "project_id", "updated_at"):
            self.assertIn(field, item)

    def test_list_unauthenticated_returns_401(self):
        self.client.logout()
        response = self.client.get("/api/graph/")
        self.assertEqual(response.status_code, 401)


class RenameProjectMapTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.pm = ProjectMap.objects.create(name="Old", source_json={}, owner=self.user)
        self.client.force_login(self.user)

    def test_rename_updates_name(self):
        res = self.client.patch(
            f"/api/graph/{self.pm.id}/",
            data=json.dumps({"name": "New"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.pm.refresh_from_db()
        self.assertEqual(self.pm.name, "New")

    def test_rename_unauthenticated_returns_401(self):
        self.client.logout()
        res = self.client.patch(
            f"/api/graph/{self.pm.id}/",
            data=json.dumps({"name": "New"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 401)

    def test_rename_non_owner_returns_403(self):
        self.client.force_login(self.other)
        res = self.client.patch(
            f"/api/graph/{self.pm.id}/",
            data=json.dumps({"name": "New"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 403)

    def test_rename_empty_name_returns_400(self):
        res = self.client.patch(
            f"/api/graph/{self.pm.id}/",
            data=json.dumps({"name": ""}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)


class DeleteProjectMapTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.pm = ProjectMap.objects.create(name="ToDelete", source_json={}, owner=self.user)
        self.client.force_login(self.user)

    def test_delete_removes_project(self):
        res = self.client.delete(f"/api/graph/{self.pm.id}/")
        self.assertEqual(res.status_code, 204)
        self.assertEqual(ProjectMap.objects.count(), 0)

    def test_delete_unauthenticated_returns_401(self):
        self.client.logout()
        res = self.client.delete(f"/api/graph/{self.pm.id}/")
        self.assertEqual(res.status_code, 401)

    def test_delete_non_owner_returns_403(self):
        self.client.force_login(self.other)
        res = self.client.delete(f"/api/graph/{self.pm.id}/")
        self.assertEqual(res.status_code, 403)


class NodeOverlayTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.other = User.objects.create_user(username="other", password="pass")
        self.pm = ProjectMap.objects.create(name="Test", source_json={}, owner=self.user)
        self.client.force_login(self.user)
        self.payload = {
            "node_type": "component",
            "system_name": "Sys",
            "container_name": "App",
            "node_name": "Widget",
            "display_name": "Widget",
            "description": "A widget",
        }

    def test_upsert_node_overlay_succeeds_for_owner(self):
        res = self.client.post(
            f"/api/graph/{self.pm.id}/overlay/node/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)

    def test_upsert_node_overlay_unauthenticated_returns_401(self):
        self.client.logout()
        res = self.client.post(
            f"/api/graph/{self.pm.id}/overlay/node/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 401)

    def test_upsert_node_overlay_non_owner_returns_403(self):
        self.client.force_login(self.other)
        res = self.client.post(
            f"/api/graph/{self.pm.id}/overlay/node/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 403)

    def test_upsert_node_overlay_on_unowned_project_returns_403(self):
        unowned = ProjectMap.objects.create(name="Unowned", source_json={})
        res = self.client.post(
            f"/api/graph/{unowned.id}/overlay/node/",
            data=json.dumps(self.payload),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 403)
