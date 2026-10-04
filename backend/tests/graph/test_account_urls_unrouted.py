"""allauth's password pages must be unrouted in production but present on previews."""

from django.test import Client, TestCase, override_settings
from django.urls import NoReverseMatch, reverse

PASSWORD_PAGES = [
    "/accounts/signup/",
    "/accounts/password/reset/",
    "/accounts/password/change/",
    "/accounts/logout/",
]


class ProductionUrlsTest(TestCase):
    def test_password_pages_are_gone(self):
        client = Client()
        for page in PASSWORD_PAGES:
            self.assertEqual(client.get(page).status_code, 404, page)

    def test_password_views_cannot_be_reversed(self):
        for name in ["account_signup", "account_reset_password", "account_logout"]:
            with self.assertRaises(NoReverseMatch, msg=name):
                reverse(name)

    def test_login_redirects_to_github_instead_of_serving_a_form(self):
        response = Client().get("/accounts/login/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/accounts/github/login/")

    def test_github_login_still_reaches_github(self):
        response = Client().get("/accounts/github/login/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("https://github.com/login/oauth/authorize"))

    def test_social_signup_does_not_explode(self):
        """It reverses account_login; dropping that name turned GitHub signup into a 500."""
        response = Client().get("/accounts/3rdparty/signup/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/accounts/login/")

    def test_oauth_cancelled_page_still_renders(self):
        self.assertEqual(Client().get("/accounts/3rdparty/login/cancelled/").status_code, 200)

    def test_catch_all_does_not_swallow_accounts(self):
        self.assertEqual(Client().get("/accounts/nonexistent/").status_code, 404)


@override_settings(ROOT_URLCONF="c4_project.preview_urls")
class PreviewUrlsTest(TestCase):
    def test_password_login_form_is_served(self):
        response = Client().get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")

    def test_github_login_is_still_routed(self):
        self.assertEqual(reverse("github_login"), "/accounts/github/login/")

    def test_api_routes_are_unchanged(self):
        """build_urlpatterns is shared, so a preview keeps every non-account route."""
        self.assertEqual(Client().get("/api/auth/me/").status_code, 401)
