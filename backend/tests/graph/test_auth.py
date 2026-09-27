from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class AuthMeTest(TestCase):
    def test_me_unauthenticated_returns_401(self):
        res = self.client.get("/api/auth/me/")
        self.assertEqual(res.status_code, 401)

    def test_me_authenticated_returns_user_data(self):
        user = User.objects.create_user(username="testuser", password="pass")
        self.client.force_login(user)
        res = self.client.get("/api/auth/me/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["username"], "testuser")
        self.assertIn("id", data)
        self.assertIn("avatar_url", data)

    @patch.dict("os.environ", {"GITHUB_APP_SLUG": "seeforceapp"})
    def test_me_reports_install_url_when_slug_configured(self):
        user = User.objects.create_user(username="testuser", password="pass")
        self.client.force_login(user)
        res = self.client.get("/api/auth/me/")
        self.assertEqual(
            res.json()["github_app_install_url"],
            "https://github.com/apps/seeforceapp/installations/new",
        )

    @patch.dict("os.environ", {"GITHUB_APP_SLUG": ""})
    def test_me_install_url_is_none_when_slug_missing(self):
        user = User.objects.create_user(username="testuser", password="pass")
        self.client.force_login(user)
        res = self.client.get("/api/auth/me/")
        self.assertIsNone(res.json()["github_app_install_url"])

    def test_me_avatar_url_empty_when_no_social_account(self):
        user = User.objects.create_user(username="nogh", password="pass")
        self.client.force_login(user)
        res = self.client.get("/api/auth/me/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["avatar_url"], "")


class AuthLogoutTest(TestCase):
    def test_logout_unauthenticated_returns_401(self):
        res = self.client.post("/api/auth/logout/")
        self.assertEqual(res.status_code, 401)

    def test_logout_clears_session(self):
        user = User.objects.create_user(username="testuser", password="pass")
        self.client.force_login(user)
        res = self.client.post("/api/auth/logout/")
        self.assertEqual(res.status_code, 200)
        # Subsequent me/ call should return 401
        res2 = self.client.get("/api/auth/me/")
        self.assertEqual(res2.status_code, 401)

    def test_logout_returns_ok_json(self):
        user = User.objects.create_user(username="testuser", password="pass")
        self.client.force_login(user)
        res = self.client.post("/api/auth/logout/")
        self.assertEqual(res.json(), {"ok": True})
