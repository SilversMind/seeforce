from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.graph.models import ProjectMap

User = get_user_model()


class ProjectMapOwnerTest(TestCase):
    def test_owner_field_accepts_user(self):
        user = User.objects.create_user(username="owner", password="pass")
        pm = ProjectMap.objects.create(name="Test", source_json={}, owner=user)
        pm.refresh_from_db()
        self.assertEqual(pm.owner, user)

    def test_owner_field_nullable(self):
        pm = ProjectMap.objects.create(name="Legacy", source_json={})
        pm.refresh_from_db()
        self.assertIsNone(pm.owner)

    def test_visibility_defaults_to_public(self):
        pm = ProjectMap.objects.create(name="Test", source_json={})
        pm.refresh_from_db()
        self.assertEqual(pm.visibility, "public")
