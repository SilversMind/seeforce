"""Password signup is closed; GitHub signup must stay open despite allauth's delegation."""

from allauth.account.adapter import get_adapter as get_account_adapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.adapter import get_adapter as get_social_adapter
from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase, override_settings

User = get_user_model()


def _sociallogin():
    return SocialLogin(
        user=User(username="octocat", email="octocat@example.invalid"),
        account=SocialAccount(provider="github", uid="99001"),
    )


class PasswordSignupClosedTest(TestCase):
    def test_signup_page_refuses(self):
        """allauth answers 200 with its closed page, so the template is the real signal."""
        response = Client().get("/accounts/signup/")
        self.assertTemplateUsed(response, "account/signup_closed.html")

    def test_posting_the_signup_form_creates_nobody(self):
        Client().post(
            "/accounts/signup/",
            {"email": "intruder@example.invalid", "password1": "hunter2hunter2", "password2": "hunter2hunter2"},
        )
        self.assertEqual(User.objects.count(), 0)

    def test_account_adapter_is_closed(self):
        request = RequestFactory().get("/accounts/signup/")
        self.assertFalse(get_account_adapter().is_open_for_signup(request))


class GithubSignupStaysOpenTest(TestCase):
    """The gate allauth consults before creating a user from a social login."""

    def test_social_adapter_is_open(self):
        request = RequestFactory().get("/accounts/github/login/callback/")
        self.assertTrue(get_social_adapter().is_open_for_signup(request, _sociallogin()))

    @override_settings(SOCIALACCOUNT_ADAPTER="allauth.socialaccount.adapter.DefaultSocialAccountAdapter")
    def test_default_social_adapter_would_have_closed_github_too(self):
        """Documents why GithubSignupAdapter exists: the default delegates to the account adapter."""
        request = RequestFactory().get("/accounts/github/login/callback/")
        adapter = get_social_adapter()
        self.assertIsInstance(adapter, DefaultSocialAccountAdapter)
        self.assertFalse(adapter.is_open_for_signup(request, _sociallogin()))
