from django.test import TestCase
from django.contrib.auth import get_user_model

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
